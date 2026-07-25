Loading OntoKG-EQ in Protégé

Place the following files together in the `ontology/` folder before opening:

- project.ttl
- core.ttl
- alignment.ttl
- shapes.ttl
- demo.ttl
- catalog-v001.xml

Load instructions:
1) Open ontology/project.ttl in Protégé Desktop. The local catalog-v001.xml maps
   ontology IRIs to the local TTL files for offline loading, so keep it in the same package.
2) Run the ELK 0.6.0 reasoner and classify.
3) Expected result: no inconsistent ontology and no unsatisfiable named class.

Note: if you have files named like `ontokg-eq-core.ttl`, rename them to `core.ttl`
(etc.) or update catalog-v001.xml accordingly.
