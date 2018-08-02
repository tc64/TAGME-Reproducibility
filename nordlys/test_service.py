import requests
import pprint
from nordlys.config import FLASK_PORT, FLASK_HOST
from nordlys.tagme.config import RHO_TH, LINK_PROB_TH, CMNS_TH, K_TH

"""
query_types = {
    "required": {
        "text": str
    },
    "optional": {
        "lnk_prob": float,
        "cmn_th": float,
        "k_th": float,
        "rho_th": float
    }
}
"""

class TagmeClient(object):
    def __init__(self):
        self.host = FLASK_HOST
        self.port = FLASK_PORT
        self.route = "/api/tagme/proc_query/v1"  # TODO coud pull from config if there

    def get_url(self):
        return "http://%s:%s%s" % (self.host, str(self.port), self.route)

    def issue_test_query(self, query_txt, rho_th, lnk_prob_th, cmn_th, k_th):
        query_req_dict = dict()
        query_req_dict["text"] = query_txt
        query_req_dict["rho_th"] = rho_th
        query_req_dict["lnk_prob_th"] = lnk_prob_th
        query_req_dict["cmn_th"] = cmn_th
        query_req_dict["k_th"] = k_th

        res = requests.post(self.get_url(), json=query_req_dict)
        return res

    def issue_and_pprint_test_query(self, query_txt, rho_th, lnk_prob_th, cmn_th, k_th):
        """

        :param query_txt:
        :param rho_th:
        :param lnk_prob_th:
        :param cmn_th:
        :param k_th:
        :return:
        """

        res = self.issue_test_query(query_txt, rho_th, lnk_prob_th, cmn_th, k_th)
        myjs = res.json()
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(myjs)

        # check myjs for proper format.


if __name__ == "__main__":
    import sys
    cl = TagmeClient()
    query_txt = sys.argv[1]
    cl.issue_and_pprint_test_query(query_txt, RHO_TH, LINK_PROB_TH, CMNS_TH, K_TH)