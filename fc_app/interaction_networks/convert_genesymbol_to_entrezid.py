#!/usr/bin/env python3

import argparse
import biothings_client
import numpy
import pandas


def get_database_dict(database: pandas.DataFrame, gene_symbols: set) -> dict:
    try:
        database_entries = set(database['query'].to_list())
    except KeyError:
        database_entries = set()
    query_gene_symbols = gene_symbols.difference(database_entries)

    if len(query_gene_symbols) > 0:
        gene_client = biothings_client.get_client("gene")
        gene_query_result = gene_client.querymany(query_gene_symbols, scopes='symbol', species='human',
                                                  fields="entrezgene, ensembl")
        gene_df = pandas.json_normalize(gene_query_result)
        database = pandas.concat([database, gene_df])
        database.to_csv(args.database)

    database = database[['query', 'entrezgene']]
    database = database.set_index('query')
    return database.to_dict()['entrezgene']


def convert_genesymbol_to_entrezid(gene_symbol: str, database: dict) -> str:
    try:
        return database[gene_symbol]
    except KeyError:
        return pandas.NA


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a gene interaction network with gene symbols to a gene '
                                                 'interaction network with entrez ids.')
    parser.add_argument('--input', type=str, required=True,
                        help='Input interaction network file with gene symbols.')
    parser.add_argument('--output', type=str, required=True,
                        help='Output interaction network file with entrez ids.')
    parser.add_argument('--database', type=str, required=True,
                        help='Database file to save already queried gene symbols.')
    args = parser.parse_args()

    # parse input files
    try:
        input_df = pandas.read_csv(args.input, sep='\t', dtype=str, index_col=None)
    except IOError:
        raise IOError("Input file not found!")

    database_df = pandas.DataFrame()
    print("Parsing Database...")
    try:
        database_df = pandas.read_csv(args.database, dtype=str, index_col=0)
    except IOError:
        pass
    except pandas.errors.EmptyDataError:
        pass

    # Database Creation and mygene.info Query
    print("Querying Genes...")
    gene_symbol_set = set(numpy.unique(input_df[['symbol1', 'symbol2']].astype('str').values))
    try:
        gene_symbol_set.remove("nan")
    except KeyError:
        pass
    database_dict = get_database_dict(database_df, gene_symbol_set)

    # Conversion of the input file
    print("Converting Input File...")
    input_df['entrezid1'] = input_df.apply(lambda x: convert_genesymbol_to_entrezid(x['symbol1'], database_dict)
                                           , axis=1)
    input_df['entrezid2'] = input_df.apply(lambda x: convert_genesymbol_to_entrezid(x['symbol2'], database_dict)
                                           , axis=1)
    input_df = input_df[['entrezid1', 'entrezid2']].dropna()

    input_df.to_csv(args.output, sep="\t", index=False)
