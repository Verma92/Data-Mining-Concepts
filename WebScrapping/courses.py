#!/usr/bin/env python
import json
import sys
import os
import getopt
from typing import Counter

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

PROG_NAME = os.path.splitext(os.path.basename(__file__))[0]

##############################################################################
##############################################################################

_BASE_URL = "https://wl11gp.neu.edu/udcprod8/"
_BASE_URL_SPCFC_SUBJ = "https://wl11gp.neu.edu"
_COURSE_SRCH = "NEUCLSS.p_class_search"
_JSON_PARAMS_FILE = 'specific_post'


# requests base+endpoint via get/post with provided parameters
# should NOT be called directly
def _call(endpoint, method, params):
    return getattr(requests, method)(urljoin(_BASE_URL, endpoint), data=params)


# get an endpoint with provided parameters
def _get(endpoint, params={}):
    return _call(endpoint, "get", params)


# post to an endpoint with provided parameters
def _post(endpoint, params={}):
    return _call(endpoint, "post", params)


##############################################################################
##############################################################################

# parses all the options in a select
# returns {value:string}
def _parse_select(select):
    return {str(option["value"]): str(option.string).strip() for option in select.find_all("option")}


# an (imperfect) Banner form parser
# provides a dictionary...
#  title: page title
#  action: form action
#  method: form method (e.g. get/post)
#  params: {
#    key: value (hidden fields and selects)
# }
def _parse_form(html):
    retval = {"params": {}}
    soup = BeautifulSoup(html, "html.parser")

    retval["title"] = str(soup.title.string)

    form = soup.find("div", {"class": "pagebodydiv"}).find("form")

    retval["action"] = str(form["action"])
    retval["method"] = str(form["method"])

    for hidden in form.find_all("input", {"type": "hidden"}):
        retval["params"][str(hidden["name"])] = str(hidden["value"])

    for select in form.find_all("select"):
        retval["params"][str(select["name"])] = _parse_select(select)

    return retval


##############################################################################
##############################################################################

# parses the term-selection form
# params include {term_code:term_name}
def termform():
    return _parse_form(_get("NEUCLSS.p_disp_dyn_sched").text)


# given the output of termform(),
# returns a term code given a term name
def term_to_code(termform, term):
    terms = termform['params']['STU_TERM_IN']
    inv_terms = {v: k for k, v in terms.items()}
    if term in inv_terms:
        return inv_terms[term]
    else:
        return None


##############################################################################
##############################################################################

# parses the empy course-search form
# for a particular term
def searchform(termcode):
    return _parse_form(_post("NEUCLSS.p_class_select", {"STU_TERM_IN": termcode}).text)


# given the output of searchform(),
# returns an instructor code given an instructor name
def instructor_to_code(searchform, instructor):
    instructors = searchform['params']['sel_instr']
    inv_instructors = {v: k for k, v in instructors.items()}
    if instructor in inv_instructors:
        return inv_instructors[instructor]
    else:
        return None


##############################################################################
##############################################################################

# parses the html of a course search, returns...
# DOCUMENT RETURN WITH EXAMPLES HERE (must be a tuple)
def _parse_course_listing(html):
    retval = {}
    soup = BeautifulSoup(html, "html.parser")
    retval["title"] = str(soup.title.string)
    # All the courses Code with their titles
    names = [title.string for title in soup.find_all("th", class_="ddtitle")]
    # All the prereqs/corereqs Code in order with the courses
    reqs = [req_name for req_name in
            [req.find_all("a") for req in soup.find_all("td", class_="dddefault", text=lambda s: s is None)]]


    result = zip(names, reqs)
    # Filtering the values and saving relevent
    result = [(tuple[0].split(" - ")[2], tuple[0].split(" - ")[0],
           sorted(list(set([alink.string for alink in tuple[1]]))))
          for tuple in result]
    result_dict = dict()
    for v in result:
        key = v[0]
        if key not in result_dict:
            result_dict[key] = (v[1], v[2])
        elif result_dict[key] == ("", []):
          result_dict[key] = (v[1], v[2])
    for link in v[2]:
        if link not in result_dict:
            result_dict[link] = ("", [])
            # Storing in a =n sorted order
    result = sorted(result_dict.items())
    return result


# Function to print name specific to a course code, but not used.
def course_link_to_name(link):
    url = _BASE_URL_SPCFC_SUBJ + link
    html = requests.post(url).text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("td", class_="nttitle").string.split(" - ")
    return (title[0], title[1])


# execute a course search request
# returns the parsed result: format of your choice (must be a tuple)
# (see _parse_course_listing for details)
def coursesearch(termcode,
                 sel_day=[], sel_subj=["%"], sel_attr=["%"],
                 sel_schd=["%"], sel_camp=["%"], sel_insm=["%"],
                 sel_ptrm=["%"], sel_levl=["%"], sel_instr=["%"], sel_seat=[],
                 sel_crn="", sel_crse="", sel_title="", sel_from_cred="", sel_to_cred="",
                 begin_hh="0", begin_mi="0", begin_ap="a",
                 end_hh="0", end_mi="0", end_ap="a"):
    params = [
        ("sel_day", "dummy"),
        ("STU_TERM_IN", termcode),
        ("sel_subj", "dummy"),
        ("sel_attr", "dummy"),
        ("sel_schd", "dummy"),
        ("sel_camp", "dummy"),
        ("sel_insm", "dummy"),
        ("sel_ptrm", "dummy"),
        ("sel_levl", "dummy"),
        ("sel_instr", "dummy"),
        ("sel_seat", "dummy"),
        ("p_msg_code", "You can not select All in Subject and All in Attribute type."),
        ("sel_crn", sel_crn),
        ("sel_title", sel_title),
        ("sel_attr", sel_attr),
        ("sel_schd", sel_schd),
        ("sel_insm", sel_insm),
        ("sel_from_cred", sel_from_cred),
        ("sel_to_cred", sel_to_cred),
        ("sel_camp", sel_camp),
        ("sel_ptrm", sel_ptrm),
        ("begin_hh", 0),
        ("begin_mi", 0),
        ("begin_ap", "a"),
        ("end_hh", 0),
        ("end_mi", 0),
        ("end_ap", "a")
    ]

    # Setting the Params provided by User :
    params.extend([("sel_levl", level) for level in sel_levl])
    params.extend([("sel_subj", subj) for subj in sel_subj])
    params.extend([("sel_instr", instr) for instr in sel_instr])
    params.append(("sel_crse", sel_crse))

    return _parse_course_listing((_post(_COURSE_SRCH, params)).text)


##############################################################################
##############################################################################

# takes in output of coursesearch
# and outputs to the console a digraph of related courses
# in DOT format
def print_course_dot(*courseinfo):
    out = open("input.gv", "w")
    out.write('digraph G {rankdir="LR";node [width=5, height=1];')
    # Print the Course Code and Titles
    for record in courseinfo:
        out.write(record[0].replace(" ", "_") + ' [ label="' + record[0] + r"\n" + record[1][0] + '" ];')
    links_arr_str = []

    # Print the links
    for record in courseinfo:

        for link in record[1][1]:
            links_arr_str.append(link.replace(" ", "_") + ' -> ' + record[0].replace(" ", "_") + ";")
    links_arr_str = sorted(links_arr_str)

    for link_str in links_arr_str:
        out.write(link_str)

    out.write("}")
    out.close()


##############################################################################
##############################################################################

# outputs usage statement and exits
def usage():
    print("usage:", PROG_NAME, "(--level)*", "(--instructor)*", "(--subject)*", "[--course]", "<term code>")
    print(" ()* can occur 0 or more times")
    print(" [] can occur 0 or 1 time")
    print(" <> must be provided")
    sys.exit(2)


# 1. parses command-line parameters
#    - uses term form to validate term
#    - uses search form to validate level, instructor, subject
# 2. performs a course search
# 3. outputs information in DOT format
def main(argv):
    opts, args = getopt.getopt(argv, "", ["level=", "instructor=", "subject=", "course="])

    #####
    if len(args) != 1:
        usage()

    term = args[0]
    termcode = term_to_code(termform(), term)

    if termcode is None:
        print("ERROR: invalid term")
        usage()

    #####

    sform = searchform(termcode)
    levels = []
    instructors = []
    subjects = []
    course = None

    for opt in opts:
        if opt[0] == "--course":
            if course is not None:
                print("ERROR: only one course allowed")
                usage()
            else:
                course = opt[1]

        elif opt[0] == "--level":
            if opt[1] in sform['params']['sel_levl'].keys():
                levels.append(opt[1])
            else:
                print("ERROR: invalid level '{}'".format(opt[1]))
                usage()

        elif opt[0] == "--instructor":
            instructorcode = instructor_to_code(sform, opt[1])
            if instructorcode is not None:
                instructors.append(instructorcode)
            else:
                print("ERROR: invalid instructor '{}'".format(opt[1]))
                usage()

        elif opt[0] == "--subject":
            if opt[1] in sform['params']['sel_subj'].keys():
                subjects.append(opt[1])
            else:
                print("ERROR: invalid subject '{}'".format(opt[1]))
                usage()

    if not len(levels):
        levels = ["%"]

    if not len(instructors):
        instructors = ["%"]

    if not len(subjects):
        subjects = ["%", "%"]

    if course is None:
        course = ""

    info = coursesearch(termcode,
                        sel_levl=levels,
                        sel_instr=instructors,
                        sel_subj=subjects,
                        sel_crse=course
                        )

    print_course_dot(*info)


if __name__ == "__main__":
    main(sys.argv[1:])
