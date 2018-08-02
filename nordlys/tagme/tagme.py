"""
TAGME implementation

@author: Faegheh Hasibi (faegheh.hasibi@idi.ntnu.no)
"""

import argparse
import math
import time
from nordlys.config import OUTPUT_DIR
from nordlys.tagme import config
from nordlys.tagme import test_coll
from nordlys.tagme.query import Query
from nordlys.tagme.mention import Mention
from nordlys.tagme.lucene_tools import Lucene

import pdb


ENTITY_INDEX = Lucene(config.INDEX_PATH)
ANNOT_INDEX = Lucene(config.INDEX_ANNOT_PATH, use_ram=True)

# ENTITY_INDEX = IndexCache("/data/wikipedia-indices/20120502-index1")
# ANNOT_INDEX = IndexCache("/data/wikipedia-indices/20120502-index1-annot/", use_ram=True)

ENTITY_INDEX.open_searcher()
ANNOT_INDEX.open_searcher()


class Tagme(object):

    DEBUG = 0

    def __init__(self, query, rho_th=.20, lnk_prob_th=.001, cmn_th=.02, k_th=.3, sf_source="wiki"):
        """
        a Tagme instance is created each time for each time a query is processed.

        :param query: nordlys.tagme.query.Query
        :param rho_th: Rho is the average between the coherence score and the link probability for a given
        entity/phrase pair. rho_th is the minimum value for an entity/phrase pair to be included in the output for a
        given phrase.
        :param lnk_prob_th: the "link probability" of a phrase. link(a) / freq(a). This is the number of instances of
        phrase a that appear as anchor text in the wikipedia data divided by the number of total times that phrase
        appears in the wikipedia data. lnk_prob_th is the minimum link probability that a phrase must have to be
        identified as a phrase that should be linked to a wikipedia article.
        :param cmn_th: the "commonness" of a phrase is the probability P(page|anchor). For a particular anchor a, each
        wikipedia page p has a P(p|a). cmn_th is the minimum commonness that a link must have to appear in the output
        from the linker. cmn_th is denoted be greek letter tau in the tagme papers. Note: There is another commonness
        threshold hard coded in Tagme.parse which is for initially enumerating candidates prior to pruning.
        :param k_th: k_th is the percentage of entity candidates that should appear in the list of possible targets for
        a given phrase. k_th is used along with cmn_th for disambiguation and pruning process. Note that this parameter
        is called epsilon in the original tagme paper.
        :param sf_source: TODO explain this
        """

        self.query = query

        # params
        self.rho_th = rho_th
        self.link_prob_th = lnk_prob_th  # 0.001
        self.cmn_th = cmn_th  # 0.02  # Tau in paper
        self.k_th = k_th  # 0.3

        #self.men_to_methods = {}  # maps each mention to the name of the phrase extraction method used to find it TODO low priority
        self.link_probs = {}  # maps each candidate phrase to its link probability
        self.candidate_entities = {}
        self.in_links = {}  #
        self.rel_scores = {}  # dictionary {men: {en: rel_score, ...}, ...}
        self.top_k_entities = {}  # {men: [(wikiUri, rel score)]} where the list is sorted greatest to least rel score.
        self.disamb_ens = {}  #

        self.sf_source = sf_source

    def parse(self):
        """
        Parses the query and returns all candidate mention-entity pairs.

        :return: candidate entities {men:{en:cmn, ...}, ...}
        """
        ens = {}  # candidate phrases are ngrams; each is mapped to
        for ngram in self.query.get_ngrams():
            mention = Mention(ngram)
            # performs mention filtering (based on the paper)
            if (len(ngram) == 1) or (ngram.isdigit()) or (mention.wiki_occurrences < 2) or (len(ngram.split()) > 6):
                continue
            link_prob = self.__get_link_prob(mention)
            if link_prob < self.link_prob_th:
                continue
            # These mentions will be kept
            self.link_probs[ngram] = link_prob
            # Filters entities by cmn threshold 0.001; this was only in TAGME source code and speeds up the process.
            # TAGME source code: it.acubelab.tagme.anchor (lines 279-284)
            # TODO configure this;
            ens[ngram] = mention.get_men_candidate_ens(0.001)  # dict of form {wiki uri: commonness}

        #pdb.set_trace()

        # filters containment mentions (based on paper)
        candidate_entities = {}  # {"mention string": {wikiUri: commonness}
        sorted_mentions = sorted(ens.keys(), key=lambda item: len(item.split()))  # sorts by mention length
        for i in range(0, len(sorted_mentions)):
            m_i = sorted_mentions[i]
            ignore_m_i = False
            for j in range(i+1, len(sorted_mentions)):
                m_j = sorted_mentions[j]
                if (m_i in m_j) and (self.link_probs[m_i] < self.link_probs[m_j]):  # filter substring mention only if link prob is less
                    ignore_m_i = True
                    break
            if not ignore_m_i:
                candidate_entities[m_i] = ens[m_i]

        self.candidate_entities = candidate_entities
        print "CANDIDATE ENTITIES: " + str(candidate_entities)
        print "LINK PROBS: " + str(self.link_probs)

        #pdb.set_trace()

        return candidate_entities

    def disambiguate(self, candidate_entities):
        """
        Performs disambiguation and link each mention to a single entity.

        :param candidate_entities: {men:{en:cmn, ...}, ...}
        :return: disambiguated entities {men:en, ...}
        """
        # Gets the relevance score
        # TODO this is the time bottleneck
        start_get_rel = time.time()
        rel_scores = {}
        for m_i in candidate_entities.keys():
            if self.DEBUG:
                print "********************", m_i, "********************"
            rel_scores[m_i] = {}
            for e_m_i in candidate_entities[m_i].keys():
                if self.DEBUG:
                    print "-- ", e_m_i
                rel_scores[m_i][e_m_i] = 0
                for m_j in candidate_entities.keys():  # all other mentions
                    if (m_i == m_j) or (len(candidate_entities[m_j].keys()) == 0):
                        continue
                    vote_e_m_j = self.__get_vote(e_m_i, candidate_entities[m_j])
                    rel_scores[m_i][e_m_i] += vote_e_m_j
                    if self.DEBUG:
                        print m_j, vote_e_m_j
        time_get_rel = time.time() - start_get_rel

        # pruning uncommon entities (based on the paper)
        start_prune_uncommon = time.time()
        self.rel_scores = {}
        for m_i in rel_scores:
            for e_m_i in rel_scores[m_i]:
                cmn = candidate_entities[m_i][e_m_i]
                if cmn >= self.cmn_th:
                    if m_i not in self.rel_scores:
                        self.rel_scores[m_i] = {}
                    self.rel_scores[m_i][e_m_i] = rel_scores[m_i][e_m_i]
        time_prune_uncommon = time.time() - start_prune_uncommon

        # DT pruning
        start_dt_prun = time.time()
        disamb_ens = {}
        for m_i in self.rel_scores:
            if len(self.rel_scores[m_i].keys()) == 0:
                continue

            # isolate top k entities based on rel score
            top_k_ens = self.__get_top_k(m_i)

            #pdb.set_trace()

            # select the entity from the top k with the best commonness
            # TODO Whether this is how the top is selected, or something else, etc., should be configurable.
            best_cmn = 0
            best_en = None
            for en in top_k_ens:
                cmn = candidate_entities[m_i][en]
                if cmn >= best_cmn:
                    best_en = en
                    best_cmn = cmn
            disamb_ens[m_i] = best_en
        time_dt_prun = time.time() - start_dt_prun

        self.disamb_ens = disamb_ens
        print "TIME GET REL: " + str(time_get_rel)
        print "TIME PRUNE UNCOMMON: " + str(time_prune_uncommon)
        print "TIME DT PRUNE: " + str(time_dt_prun)

        #pdb.set_trace()

        return disamb_ens

    def prune(self, dismab_ens):
        """
        Performs AVG pruning.

        :param dismab_ens: {men: en, ... }
        :return: {men: (en, score), ...}
        """
        linked_ens = {}
        for men, en in dismab_ens.iteritems():
            coh_score = self.__get_coherence_score(men, en, dismab_ens)
            rho_score = (self.link_probs[men] + coh_score) / 2.0
            if rho_score >= self.rho_th:
                linked_ens[men] = (en, rho_score)
        return linked_ens

    def __get_link_prob(self, mention):
        """
        Gets link probability for the given mention.
        Here, in fact, we are computing key-phraseness.
        """

        pq = ENTITY_INDEX.get_phrase_query(mention.text, Lucene.FIELDNAME_CONTENTS)
        mention_freq = ENTITY_INDEX.searcher.search(pq, 1).totalHits
        if mention_freq == 0:
            return 0
        if self.sf_source == "wiki":
            link_prob = mention.wiki_occurrences / float(mention_freq)
            # This is TAGME implementation, from source code:
            # link_prob = float(mention.wiki_occurrences) / max(mention_freq, mention.wiki_occurrences)
        elif self.sf_source == "facc":
            link_prob = mention.facc_occurrences / float(mention_freq)
        return link_prob

    def __get_vote(self, entity, men_cand_ens):
        """
        vote_e = sum_e_i(mw_rel(e, e_i) * cmn(e_i)) / i

        :param entity: en
        :param men_cand_ens: {en: cmn, ...}
        :return: voting score
        """
        entity = entity if self.sf_source == "wiki" else entity[0]
        vote = 0
        for e_i, cmn in men_cand_ens.iteritems():
            e_i = e_i if self.sf_source == "wiki" else e_i[0]
            mw_rel = self.__get_mw_rel(entity, e_i)
            # print "\t", e_i, "cmn:", cmn, "mw_rel:", mw_rel
            vote += cmn * mw_rel
        vote /= float(len(men_cand_ens))
        return vote

    def __get_mw_rel(self, e1, e2):
        """
        Calculates Milne & Witten relatedness for two entities.
        This implementation is based on Dexter implementation (which is similar to TAGME implementation).
          - Dexter implementation: https://github.com/dexter/dexter/blob/master/dexter-core/src/main/java/it/cnr/isti/hpc/dexter/relatedness/MilneRelatedness.java
          - TAGME: it.acubelab.tagme.preprocessing.graphs.OnTheFlyArrayMeasure
        """
        if e1 == e2:  # to speed-up
            return 1.0
        en_uris = tuple(sorted({e1, e2}))
        ens_in_links = [self.__get_in_links([en_uri]) for en_uri in en_uris]
        if min(ens_in_links) == 0:
            return 0
        conj = self.__get_in_links(en_uris)  # TODO this is redundant, we have already gotten inlinks for each en_uri in en_uris!
        if conj == 0:
            return 0
        numerator = math.log(max(ens_in_links)) - math.log(conj)
        denominator = math.log(ANNOT_INDEX.num_docs()) - math.log(min(ens_in_links))
        rel = 1 - (numerator / denominator)
        if rel < 0:
            return 0
        return rel

    def __get_in_links(self, en_uris):
        """
        returns "and" occurrences of entities in the corpus.

        :param en_uris: list of dbp_uris
        """
        en_uris = tuple(sorted(set(en_uris)))
        if en_uris in self.in_links:
            return self.in_links[en_uris]

        term_queries = []
        for en_uri in en_uris:
            term_queries.append(ANNOT_INDEX.get_id_lookup_query(en_uri, Lucene.FIELDNAME_CONTENTS))  # term_queries is a list of lucene TermQuery objects
        and_query = ANNOT_INDEX.get_and_query(term_queries)
        self.in_links[en_uris] = ANNOT_INDEX.searcher.search(and_query, 1).totalHits
        return self.in_links[en_uris]

    def __get_coherence_score(self, men, en, dismab_ens):
        """
        coherence_score = sum_e_i(rel(e_i, en)) / len(ens) - 1

        :param en: entity
        :param dismab_ens: {men:  (dbp_uri, fb_id), ....}
        """
        coh_score = 0
        for m_i, e_i in dismab_ens.iteritems():
            if m_i == men:
                continue
            coh_score += self.__get_mw_rel(e_i, en)
        coh_score = coh_score / float(len(dismab_ens.keys()) - 1) if len(dismab_ens.keys()) - 1 != 0 else 0
        return coh_score

    def __get_top_k(self, mention):
        """Returns top-k percent of the entities based on rel score."""
        k = int(round(len(self.rel_scores[mention].keys()) * self.k_th))
        k = 1 if k == 0 else k
        sorted_rel_scores = sorted(self.rel_scores[mention].items(), key=lambda item: item[1], reverse=True)
        self.top_k_entities[mention] = sorted_rel_scores
        #pdb.set_trace()

        top_k_ens = []
        count = 1
        prev_rel_score = sorted_rel_scores[0][1]
        for en, rel_score in sorted_rel_scores:
            if rel_score != prev_rel_score:
                count += 1
            if count > k:
                break
            top_k_ens.append(en)
            prev_rel_score = rel_score
        return top_k_ens


class TagmeQueryProcessor(object):
    """

    """

    def __init__(self):
        """

        """
        self.rho_th = config.RHO_TH
        self.lnk_prob_th = config.LINK_PROB_TH
        self.cmn_th = config.CMNS_TH
        self.k_th = config.K_TH

    def _build_response(self, tagme, linked_ens):
        """
        build response dictionary to return to caller. do not jsonify here.
        :param tagme: Tagme object that has just processed a query (parse, disambig, prune)
        :param linked_ens: output from prune step
        :return: dictoinary confirming to current API spec
        """

        res_dict = dict()

        res_dict["el_cands"] = list()
        for men in tagme.link_probs:

            # build element entry for this mention
            entry = dict()
            entry["str"] = men
            entry["start"] = -1  # TODO get this value
            entry["end"] = -1  # TODO get this value
            entry["lnk_prob"] = tagme.link_probs[men]
            entry["el_extr_mtds"] = [{"name": "tagme_anchor"}]  # TODO get this value correctly

            entry["wiki_links"] = list()
            if men in linked_ens:
                selected_ent = linked_ens[men][0]
                selected_ent_rho = linked_ens[men][1]

                for wiki_uri_rel_pair in tagme.top_k_entities[men]:  # TODO handle case where nothing is there? possible?

                    # build wikilink entry for this element entry
                    wiki_link_entry = dict()
                    wiki_uri = wiki_uri_rel_pair[0]
                    rel_score = wiki_uri_rel_pair[1]
                    wiki_link_entry["uri"] = wiki_uri
                    wiki_link_entry["rel"] = rel_score
                    wiki_link_entry["cmn"] = tagme.candidate_entities[men][wiki_uri]
                    if wiki_uri == selected_ent:
                        wiki_link_entry["rho"] = selected_ent_rho
                    else:
                        wiki_link_entry["rho"] = None

                    entry["wiki_links"].append(wiki_link_entry)  # add wikilink entry

            res_dict["el_cands"].append(entry)  # add entry

        return res_dict

    def _process_query(self, query_txt, rho_th, lnk_prob_th, cmn_th, k_th):
        """

        :param query_txt:
        :param rho_th:
        :param link_prob_th:
        :param cmn_th:
        :param k_th:
        :return:
        """

        # TODO log steps here for debugging
        # TODO generate qid when we are logging. can just make it query_timestamp

        # create query and tagme objects
        qid = 0
        tagme = Tagme(Query(qid, query_txt), rho_th=rho_th, lnk_prob_th=lnk_prob_th, cmn_th=cmn_th, k_th=k_th)

        # run tagme steps: parse, disambiguate, and prune
        cand_ens = tagme.parse()
        disamb_ens = tagme.disambiguate(cand_ens)
        linked_ens = tagme.prune(disamb_ens)

        #pdb.set_trace()

        # build response dictionary from results
        res_dict = self._build_response(tagme, linked_ens)

        return res_dict

    def process_query(self, query_req_dict):
        """
        handle incoming query dictionary; choose thresholds/parameters values for this query; pass info to
        helper method and get response dictionary to return.
        :param query_req_dict:
        :return: res_dict
        """

        query_txt = query_req_dict["text"]
        rho_th = self.rho_th if "rho_th" not in query_req_dict else query_req_dict["rho_th"]
        lnk_prob_th = self.lnk_prob_th if "lnk_prob_th" not in query_req_dict else query_req_dict["lnk_prob_th"]
        cmn_th = self.cmn_th if "cmn_th" not in query_req_dict else query_req_dict["cmn_th"]
        k_th = self.k_th if "k_th" not in query_req_dict else query_req_dict["k_th"]

        res_dict = self._process_query(query_txt=query_txt, rho_th=rho_th, lnk_prob_th=lnk_prob_th, cmn_th=cmn_th,
                                       k_th=k_th)

        return res_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-th", "--threshold", help="score threshold", type=float, default=0)
    parser.add_argument("-data", help="Data set name", choices=['y-erd', 'erd-dev', 'wiki-annot30', 'wiki-disamb30'])
    args = parser.parse_args()

    if args.data == "erd-dev":
        queries = test_coll.read_erd_queries()
    elif args.data == "y-erd":
        queries = test_coll.read_yerd_queries()
    elif args.data == "wiki-annot30":
        queries = test_coll.read_tagme_queries(config.WIKI_ANNOT30_SNIPPET)
    elif args.data == "wiki-disamb30":
        queries = test_coll.read_tagme_queries(config.WIKI_DISAMB30_SNIPPET)

    out_file_name = OUTPUT_DIR + "/" + args.data + "_tagme_wiki10.txt"
    open(out_file_name, "w").close()
    out_file = open(out_file_name, "a")

    # process the queries
    for qid, query in sorted(queries.items(), key=lambda item: int(item[0]) if item[0].isdigit() else item[0]):
        print "[" + qid + "]", query
        tagme = Tagme(Query(qid, query), args.threshold)
        print "  parsing ..."
        cand_ens = tagme.parse()
        print "  disambiguation ..."
        disamb_ens = tagme.disambiguate(cand_ens)
        print "  pruning ..."
        linked_ens = tagme.prune(disamb_ens)

        out_str = ""
        for men, (en, score) in linked_ens.iteritems():
            out_str += str(qid) + "\t" + str(score) + "\t" + en + "\t" + men + "\tpage-id" + "\n"
        print out_str, "-----------\n"
        out_file.write(out_str)

    print "output:", out_file_name

if __name__ == "__main__":
    #main()
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    qp = TagmeQueryProcessor()
    pp.pprint(qp.process_query({"text": "What Is Target Yield For Mexico 10 Year Government Bond By End Of 2018"}))
