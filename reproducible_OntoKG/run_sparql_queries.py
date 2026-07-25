#!/usr/bin/env python3
"""
Execute CQ SPARQL queries and save results to CSV files in evaluation/
"""
import os
import sys
from pathlib import Path
from rdflib import Graph

def run_sparql_query(graph, query_file, output_file):
    """Execute a SPARQL query and save results to CSV"""
    with open(query_file, 'r') as f:
        query = f.read()
    
    print(f"  Executing {Path(query_file).name}...")
    try:
        results = graph.query(query)
        
        # Convert results to CSV
        with open(output_file, 'w', newline='') as csvf:
            # Write header
            if results:
                vars_list = list(results.vars)
                csvf.write(','.join(str(v) for v in vars_list) + '\n')
                
                # Write rows
                for row in results:
                    row_vals = []
                    for var in vars_list:
                        val = row.get(var)
                        if val is None:
                            row_vals.append('')
                        else:
                            row_vals.append(str(val).replace(',', ';'))
                    csvf.write(','.join(row_vals) + '\n')
                
                print(f"    ✓ {len(results)} rows → {output_file}")
            else:
                csvf.write("# No results\n")
                print(f"    ⊘ No results → {output_file}")
    except Exception as e:
        print(f"    ✗ Error: {e}")

def main():
    repo_root = Path(__file__).parent
    data_dir = repo_root / "data"
    sparql_dir = repo_root / "queries"
    eval_dir = repo_root / "evaluation"
    
    print(f"Loading graph from {data_dir / 'demo.ttl'}...")
    graph = Graph()
    graph.parse(str(data_dir / "demo.ttl"), format="turtle")
    print(f"  Loaded {len(graph)} triples\n")
    
    # Execute each CQ query
    for cq_num in range(1, 6):
        query_file = sparql_dir / f"CQ{cq_num}_CASE_01.rq"
        output_file = eval_dir / f"CQ{cq_num}_CASE_01_results.csv"
        
        if query_file.exists():
            run_sparql_query(graph, query_file, output_file)
        else:
            print(f"  ⊘ {query_file.name} not found")
    
    print("\n✓ SPARQL query execution complete")

if __name__ == "__main__":
    main()
