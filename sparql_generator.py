import os
from groq import Groq
from rdflib import Graph


MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You must translate the user's request into a SPARQL query, and return only the query, no more information. . The graph is about libraries, their versions, modules, changes and programming languages

Below is the graph schema being used in the project so you can successfully generate the queries, Do not invent any other class, relationship or attribute, only use the ones that are in the schema:

Classes:

* Library
* Version
* Module
* Change
* Language

Relationships:

* Library hasVersion Version
* Library hasModule Module
* Version hasChange Change
* Library requires Language
* Change changeModule Module

Attributes:

* Version: versionNumber:String
* Library: libraryName:String
* Change:
** typeChange:String (This can only have tree values: 'breaking', 'feature' and 'bugfix')
** descriptionChange:String
** fixChange: string
* Module: Not attributes, but the name of the module is important to be used in the queries, for example if the module is tf.lite, in the graph we replace the '.' for '_', so its Module_tf_lite, so Version2.20 is going to be Version_2_20_0.
* Language: Not attributes.

Use the following examples as a guide:

User: Dame todos los changes de tf.lite con su versión, incluyendo el fix si existe.
SPARQL Query:
PREFIX ex: <http://example.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?versionNum ?desc ?fix
WHERE {
	?version  ex:versionNumber      ?versionNum .
	?version  ex:hasChange          ?change .
	?change   ex:changeModule       ex:Module_tf_lite .
	?change   ex:descriptionChange  ?desc .
	OPTIONAL {
	?change  ex:fixChange  ?fix .
	FILTER(STR(?fix) != "")
}
}

User: ¿En qué versiones hubo breaking changes relacionados con Python?
SPARQL Query:
PREFIX ex: <http://example.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?versionNum ?desc
WHERE {
	?version  ex:versionNumber      ?versionNum .
	?version  ex:hasChange          ?change .
	?change   ex:typeChange         "breaking"^^xsd:string .
	?change   ex:descriptionChange  ?desc .
	FILTER(CONTAINS(STR(?desc), "Python"))
}

User: ¿Qué módulos tuvieron changes en la versión 2.21.0?
SPARQL Query:
PREFIX ex: <http://example.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?modulo
WHERE {
    ex:Version_2_21_0  ex:hasChange    ?change .
    ?change           ex:changeModule  ?modulo .
}

User: ¿Hay algún bugfix relacionado con save_model?
SPARQL Query:
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

You can use these examples to guide your translation. Remember to only return the SPARQL query, and nothing else.
"""

client = Groq(api_key="") #os.environ.get("GROQ_API_KEY")


def reformulate(question: str, sparql: str, error: str) -> str:
    prompt = (
        f"This SPARQL query has an error. Fix it and return only the corrected query.\n\n"
        f"Original question: {question}\n"
        f"Query with error:\n{sparql}\n"
        f"Error: {error}"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def verify(question: str, sparql: str) -> str:
    prompt = (
        f"This query returned 0 results. Generate a more general version by loosening constraints — "
        f"for example, remove unnecessary FILTERs or replace specific values with variables. "
        f"Return only the query.\n\n"
        f"Original question: {question}\n"
        f"Query:\n{sparql}"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def generate_answer(question: str, results: list) -> str:
    results_text = "\n".join([str(row) for row in results])
    prompt = (
        f"Answer the following user question clearly and concisely, "
        f"based solely on this data:\n\n"
        f"Question: {question}\n"
        f"Data: {results_text}"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def generate_sparql(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def agent(question: str, g: Graph) -> str:
    query = generate_sparql(question)
    print(f"Generated SPARQL query:\n{query}\n")
    for attempt in range(10):
        try:
            results = list(g.query(query))
            break
        except Exception as e:
            if attempt == 9:
                return "Perdon, soy mongolo y despues de 10 intentos no logre generar la query SparQL para poder responder tu pregunta"
            query = reformulate(question, query, str(e))

    if len(results) == 0:
        query = verify(question, query)
        for attempt in range(10):
            try:
                results = list(g.query(query))
                break
            except Exception as e:
                if attempt == 9:
                    return "Perdon, soy mongolo y despues de 10 intentos no logre generar la query SparQL para poder responder tu pregunta"
                query = reformulate(question, query, str(e))
        if len(results) == 0:
            return "No tengo información suficiente para responder esa pregunta."

    return generate_answer(question, results)


if __name__ == "__main__":
    questions = [
        "¿Qué cambios hubo en la versión 2.19.0?",
        "¿Qué módulos tuvieron features en TensorFlow?",
        "¿Hay algún bugfix relacionado con save_model?",
        "Dame todos los breaking changes con su fix si existe",
    ]

    ttl_path = os.path.join(os.path.dirname(__file__), "ontology.ttl")
    g = Graph()
    g.parse(ttl_path, format="turtle")

    for question in questions:
        print(f"\n{'='*60}")
        print(f"Pregunta: {question}")
        answer = agent(question, g)
        print(f"Respuesta: {answer}")
