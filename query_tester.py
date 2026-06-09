import os
from rdflib import Graph

ttl_path = os.path.join(os.path.dirname(__file__), "ontology.ttl")
g = Graph()
g.parse(ttl_path, format="turtle")

query = """
PREFIX ex: <http://example.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?versionNum ?desc ?fix
WHERE {
    ?version  ex:versionNumber      ?versionNum .
    ?version  ex:hasChange          ?change .
    ?change   ex:descriptionChange  ?desc .
    ?change   ex:typeChange        ?type .
    FILTER(?type = "bugfix" && CONTAINS(STR(?desc), "save_model"))
    OPTIONAL {
        ?change  ex:fixChange  ?fix .
        FILTER(STR(?fix) != "")
    }
}
"""

results = list(g.query(query))
print(f"Results: {len(results)}")
for row in results:
    print(row)
