from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace, Literal
from rdflib.namespace import XSD
import hashlib

# definer namespace
EX = Namespace("http://example.org/ontology#")

# crear grafo
g = Graph()
g.bind("ex", EX)

def populate_graph(parsed_release: dict, graph: Graph, library_uri=None) -> None:
    """
    Pobla el grafo RDF con la información de una release.

    Args:
        parsed_release: Dict con 'version' y 'changes'
        graph: Grafo RDF donde agregar los datos
        library_uri: URI de la librería padre (para vincular versiones)
    """
    version_number = parsed_release['version']

    # Crear instancia de Version
    version_uri = EX[f"Version_{version_number.replace('.', '_')}"]
    graph.add((version_uri, RDF.type, EX.Version))
    graph.add((version_uri, EX.versionNumber, Literal(version_number, datatype=XSD.string)))

    # Vincular version a la librería si existe
    if library_uri:
        graph.add((library_uri, EX.hasVersion, version_uri))

    # Procesar cada change
    for change in parsed_release['changes']:
        description = change['description'].strip()

        # Filtrar descriptions de mala calidad (headers markdown)
        if not description or description.endswith(':') or len(description) < 10:
            continue

        # Crear URI única para el change usando MD5 del description
        change_hash = hashlib.md5(description.encode()).hexdigest()[:8]
        change_uri = EX[f"Change_{version_number.replace('.', '_')}_{change_hash}"]

        # Crear instancia de Change
        graph.add((change_uri, RDF.type, EX.Change))
        graph.add((change_uri, EX.typeChange, Literal(change['type'], datatype=XSD.string)))
        graph.add((change_uri, EX.descriptionChange, Literal(description, datatype=XSD.string)))
        graph.add((change_uri, EX.fixChange, Literal(change['fix'], datatype=XSD.string)))

        # Vincular change a version
        graph.add((version_uri, EX.hasChange, change_uri))

        # Procesar módulo si existe
        if change['module']:
            module_name = change['module'].replace('.', '_')
            module_uri = EX[f"Module_{module_name}"]

            # Verificar si el módulo ya existe en el grafo
            module_exists = (module_uri, RDF.type, EX.Module) in graph

            # Si no existe, crear la instancia
            if not module_exists:
                graph.add((module_uri, RDF.type, EX.Module))

            # Vincular change a module
            graph.add((change_uri, EX.changeModule, module_uri))

# definer clases
g.add((EX.Library, RDF.type, OWL.Class))
g.add((EX.Library, RDFS.label, Literal("Library")))

g.add((EX.Version, RDF.type, OWL.Class))
g.add((EX.Version, RDFS.label, Literal("Version")))


g.add((EX.Module, RDF.type, OWL.Class))
g.add((EX.Module, RDFS.label, Literal("Module")))


g.add((EX.Change, RDF.type, OWL.Class))
g.add((EX.Change, RDFS.label, Literal("Change")))


g.add((EX.Language, RDF.type, OWL.Class))
g.add((EX.Language, RDFS.label, Literal("Language")))

#Anadir relaciones
g.add((EX.hasVersion, RDF.type, OWL.ObjectProperty))
g.add((EX.hasVersion, RDFS.domain, EX.Library))
g.add((EX.hasVersion, RDFS.range, EX.Version))

g.add((EX.hasModule, RDF.type, OWL.ObjectProperty))
g.add((EX.hasModule, RDFS.domain, EX.Library))
g.add((EX.hasModule, RDFS.range, EX.Module))

g.add((EX.hasChange, RDF.type, OWL.ObjectProperty))
g.add((EX.hasChange, RDFS.domain, EX.Version))
g.add((EX.hasChange, RDFS.range, EX.Change))

g.add((EX.requires, RDF.type, OWL.ObjectProperty))
g.add((EX.requires, RDFS.domain, EX.Library))
g.add((EX.requires, RDFS.range, EX.Language))

g.add((EX.changeModule, RDF.type, OWL.ObjectProperty))
g.add((EX.changeModule, RDFS.domain, EX.Change))
g.add((EX.changeModule, RDFS.range, EX.Module)) #change afecta a un módulo específico

#Anadir atributos
g.add((EX.versionNumber, RDF.type, OWL.DatatypeProperty))
g.add((EX.versionNumber, RDFS.domain, EX.Version))
g.add((EX.versionNumber, RDFS.range, XSD.string))

g.add((EX.libraryName, RDF.type, OWL.DatatypeProperty))
g.add((EX.libraryName, RDFS.domain, EX.Library))
g.add((EX.libraryName, RDFS.range, XSD.string))

g.add((EX.typeChange, RDF.type, OWL.DatatypeProperty))
g.add((EX.typeChange, RDFS.domain, EX.Change))
g.add((EX.typeChange, RDFS.range, XSD.string))

g.add((EX.descriptionChange, RDF.type, OWL.DatatypeProperty))
g.add((EX.descriptionChange, RDFS.domain, EX.Change))
g.add((EX.descriptionChange, RDFS.range, XSD.string))

g.add((EX.fixChange, RDF.type, OWL.DatatypeProperty))
g.add((EX.fixChange, RDFS.domain, EX.Change))
g.add((EX.fixChange, RDFS.range, XSD.string))

# crear instancia ejemplo
# Crear una instancia de TensorFlow
library1 = EX.TensorFlow
g.add((library1, RDF.type, EX.Library))
g.add((library1, EX.libraryName, Literal("TensorFlow", datatype=XSD.string)))

# Crear las instancias de las Versiones
version1 = EX.Version_2_1_0
g.add((version1, RDF.type, EX.Version))
g.add((version1, EX.versionNumber, Literal("2.1.0", datatype=XSD.string)))
g.add((library1, EX.hasVersion, version1))

version2 = EX.Version_2_1_3
g.add((version2, RDF.type, EX.Version))
g.add((version2, EX.versionNumber, Literal("2.1.3", datatype=XSD.string)))
g.add((library1, EX.hasVersion, version2))

# Crear una instancia de Change
change1 = EX.Change_v_2_1_3
g.add((change1, RDF.type, EX.Change))
g.add((change1, EX.typeChange, Literal("breaking", datatype=XSD.string)))
g.add((change1, EX.descriptionChange, Literal("Se eliminó la función tf.contrib.layers.batch_norm", datatype=XSD.string)))
g.add((change1, EX.fixChange, Literal("Reemplazar tf.contrib.layers.batch_norm por tf.keras.layers.BatchNormalization", datatype=XSD.string)))
g.add((version2, EX.hasChange, change1))

# Crear una instancia de Module
module1 = EX.Module_keras_optimizers
g.add((module1, RDF.type, EX.Module))
g.add((library1, EX.hasModule, module1))

# Asociar el cambio al módulo específico
g.add((change1, EX.changeModule, module1))  

# Crear una instancia de Language
language1 = EX.Python
g.add((language1, RDF.type, EX.Language))
g.add((library1, EX.requires, language1))

# Limpiar solo las instancias de datos de ejemplo (no las definiciones)
g.remove((EX.TensorFlow, None, None))
g.remove((EX.Version_2_1_0, None, None))
g.remove((EX.Version_2_1_3, None, None))
g.remove((EX.Change_v_2_1_3, None, None))
g.remove((EX.Module_keras_optimizers, None, None))
g.remove((EX.Python, None, None))
g.remove((None, EX.hasVersion, None))
g.remove((None, EX.hasChange, None))
g.remove((None, EX.changeModule, None))
g.remove((None, EX.hasModule, None))
g.remove((None, EX.requires, None))

# Crear la librería TensorFlow y vincularla
library_uri = EX.TensorFlow
g.add((library_uri, RDF.type, EX.Library))
g.add((library_uri, EX.libraryName, Literal("TensorFlow", datatype=XSD.string)))

# Poblar el grafo con datos de releases parseadas
from parse_release import parse_release
import requests

url = "https://api.github.com/repos/tensorflow/tensorflow/releases"
response = requests.get(url)
data = response.json()

parsed_releases = [parse_release(release) for release in data if '-rc' not in release['tag_name'].lower()][:5]
for parsed_release in parsed_releases:
    populate_graph(parsed_release, g, library_uri)

# Guardar la ontología en un archivo TTL
g.serialize(destination="/home/fabian/Documents/my_prj/phdtest/ontology.ttl", format="turtle")
print("✓ Ontología guardada en ontology.ttl")