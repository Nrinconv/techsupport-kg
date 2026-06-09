import os
from groq import Groq
from rdflib import Graph
import json

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """

You are an expert in SPARQL language and knowledge graphs.

You must translate the user's request into a SPARQL query, and return only the query, no more information.

The graph is about libraries, their versions, modules, changes and programming languages.

Below is the graph schema being used in the project so you can successfully generate the queries, do not invent any other class, relationship or attribute, only use the ones that are in the schema:

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


def agent(question: str, g: Graph) -> tuple[str, str]:
    query = generate_sparql(question)
    # print(f"Generated SPARQL query:\n{query}\n")
    for attempt in range(10):
        try:
            results = list(g.query(query))
            break
        except Exception as e:
            if attempt == 9:
                return query, "Sorry, I am dumb and after 10 attempts I failed to generate a valid SPARQL query to answer your question."
            query = reformulate(question, query, str(e))

    if len(results) == 0:
        query = verify(question, query)
        for attempt in range(10):
            try:
                results = list(g.query(query))
                break
            except Exception as e:
                if attempt == 9:
                    return query, "Sorry, I am dumb and after 10 attempts I failed to generate a valid SPARQL query to answer your question."
                query = reformulate(question, query, str(e))
        if len(results) == 0:
            return query, "I don't have enough information to answer that question."

    return query, generate_answer(question, results)


def llm_as_a_judge(question: str, expected: str, actual: str) -> dict:
    prompt = (
        f"You are an expert evaluator for question-answering systems over knowledge graphs. "
        f"Your task is to judge whether the agent's answer is semantically equivalent to the expected answer, given the original question. "
        f"Focus on whether the core meaning and factual content match, not on exact wording, formatting, or phrasing. "
        f"Mark the answer as correct if the agent conveys the same information, even if expressed differently. "
        f"Reply with a JSON object with two fields: "
        f"\"correct\" (true or false) and \"justification\" (one sentence explaining your decision).\n\n"
        f"User question: {question}\n"
        f"Expected answer: {expected}\n"
        f"Agent answer: {actual}"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content)


def evaluate(question: str, expected: str, actual: str, final_query: str, g: Graph) -> dict:
    try:
        g.query(final_query)
        syntax_valid = True
    except Exception:
        syntax_valid = False

    judge = llm_as_a_judge(question, expected, actual)

    return {
        "syntax_valid": syntax_valid,
        "semantic_correct": judge.get("correct", False),
        "justification": judge.get("justification", ""),
    }


if __name__ == "__main__":
    # questions = [
    #     "What changes were made in version 2.19.0?",
    #     "Which modules had features in TensorFlow?",
    #     "Is there any bugfix related to save_model?",
    #     "Give me all breaking changes with their fix if it exists",
    # ]
    # for question in questions:
    #     print(f"\n{'='*60}")
    #     print(f"Question: {question}")
    #     answer = agent(question, g)
    #     print(f"Answer: {answer}")

    ttl_path = os.path.join(os.path.dirname(__file__), "ontology.ttl")
    g = Graph()
    g.parse(ttl_path, format="turtle")

    with open(os.path.join(os.path.dirname(__file__), "benchmark.json")) as f:
        benchmark = json.load(f)

    results_list = []
    for item in benchmark:
        question = item["question"]
        expected = item["expected"]

        query, answer = agent(question, g)
        result = evaluate(question, expected, answer, query, g)
        results_list.append(result)

        print(f"\n{'='*60}")
        print(f"Question:    {question}")
        print(f"Expected:    {expected}")
        print(f"Answer:      {answer}")
        print(f"Syntax OK:   {result['syntax_valid']}")
        print(f"Semantic OK: {result['semantic_correct']}")
        print(f"Justification: {result['justification']}")

    syntax_score = sum(1 for r in results_list if r['syntax_valid'])
    semantic_score = sum(1 for r in results_list if r['semantic_correct'])
    total = len(benchmark)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {syntax_score}/{total} valid queries | {semantic_score}/{total} correct answers")
