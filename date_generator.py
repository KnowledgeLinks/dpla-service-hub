"""Date Generator class a stop-gap until rdfframework date utilities are ready"""
__author__ = "Jeremy Nelson"

import datetime
import re

import rdflib

RANGE_4YEARS = re.compile(r"(\d{4})-(\d{4})\b")
RANGE_4to2YEARS = re.compile(r"(\d{4})-(\d{2})\b")
YEAR = re.compile(r"\b(\d{4})\b")

BF = rdflib.Namespace("http://id.loc.gov/ontologies/bibframe/")

class DateGenerator(object):
    """Class dates a raw string and attempts to generate RDF associations"""

    def __init__(self, **kwargs):
        self.graph = kwargs.get("graph")
        self.work = self.graph.value(predicate=rdflib.RDF.type,
                                     object=BF.Work)


    def add_range(self, start, end):
        for date_row in range(int(start), int(end)+1):
            self.add_year(date_row)
    
    def add_4_years(self, result):
        self.graph.add((self.work, BF.temporalCoverage, rdflib.Literal(result.string)))
        start, end = result.groups()
        self.add_range(start, end)

    def add_4_to_2_years(self, result):
        start_year, stub_year = result.groups()
        end_year = "{}{}".format(start_year[0:2], stub_year)
        self.graph.add((self.work, 
                        BF.temporalCoverage, 
                        rdflib.Literal("{} to {}".format(start_year, end_year))))
        self.add_range(start_year, end_year)

    def add_year(self, year):
        bnode = rdflib.BNode()
        self.graph.add((self.work, BF.subject, bnode))
        self.graph.add((bnode, rdflib.RDF.type, BF.Temporal))
        self.graph.add((bnode, rdflib.RDF.value, rdflib.Literal(year)))

    def run(self, raw_date, delimiter=","):
        if len(raw_date) == 4 and YEAR.search(raw_date):
            return self.add_year(raw_date)
        result = RANGE_4YEARS.search(raw_date)
        if result is not None:
            return self.add_4_years(result)
        result = RANGE_4to2YEARS.search(raw_date)
        if result is not None:
            return self.add_4_to_2_years(result)
        if delimiter in raw_date:
            for comma_row in raw_date.split(delimiter):
                self.run(comma_row, delimiter)

