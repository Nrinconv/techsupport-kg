from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace, Literal
from rdflib.namespace import XSD

# definer namespace
EX = Namespace("http://example.org/ontology#")

# crear grafo
g = Graph()
g.bind("ex", EX)

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
# o e major solo
# g.add((EX.Library, EX.hasVersion, EX.Version))

g.add((EX.hasModule, RDF.type, OWL.ObjectProperty))
g.add((EX.hasModule, RDFS.domain, EX.Library))
g.add((EX.hasModule, RDFS.range, EX.Module))

g.add((EX.hasChange, RDF.type, OWL.ObjectProperty))
g.add((EX.hasChange, RDFS.domain, EX.Version))
g.add((EX.hasChange, RDFS.range, EX.Change))

g.add((EX.requires, RDF.type, OWL.ObjectProperty))
g.add((EX.requires, RDFS.domain, EX.Library))
g.add((EX.requires, RDFS.range, EX.Language))

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

# Crear una instancia de Language
language1 = EX.Python
g.add((language1, RDF.type, EX.Language))
g.add((library1, EX.requires, language1))

#resultados
results = g.query("""
    PREFIX ex: <http://example.org/ontology#>
    SELECT ?library ?version ?changeType ?changeDescription ?changeFix
    WHERE {
        ?library a ex:Library ;
                 ex:hasVersion ?version .
        ?version ex:hasChange ?change .
        ?change ex:typeChange ?changeType ;
                ex:descriptionChange ?changeDescription ;
                ex:fixChange ?changeFix .
                  FILTER(?changeType = "breaking") .
    }
""")
for row in results:
    # print(row)
    print(f"Library: {row.library}, \nVersion: {row.version}, \nChange Type: {row.changeType}, \nDescription: {row.changeDescription}, \nFix: {row.changeFix}")

# Guardar la ontología en un archivo TTL
g.serialize(destination="/home/fabian/Documents/my_prj/phdtest/ontology.ttl", format="turtle")
print("✓ Ontología guardada en ontology.ttl")