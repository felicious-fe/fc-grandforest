#!/bin/bash

if [[ ! -d "source" ]]; then
    mkdir "source"
fi

FIRST_LINE="id1\tid2\tsymbol1\tsymbol2\tpubmedid"

# BioGRID Source File:
BIOGRID_VERSION="4.1.190"
BIOGRID_SOURCE="BIOGRID-ALL-${BIOGRID_VERSION}"
if [[ ! -f "source/${BIOGRID_SOURCE}.tab3.txt" ]]; then   
    if [[ ! -f "source/${BIOGRID_SOURCE}.tab3.zip" ]]; then
	    wget -O "source/${BIOGRID_SOURCE}.tab3.zip" "https://downloads.thebiogrid.org/Download/BioGRID/Release-Archive/BIOGRID-${BIOGRID_VERSION}/${BIOGRID_SOURCE}.tab3.zip"
    fi
    unzip "source/${BIOGRID_SOURCE}.tab3.zip" -d "source/"
    rm "source/${BIOGRID_SOURCE}.tab3.zip"
fi
awk -F "\t" '{print $4"\t"$5"\t"$8"\t"$9"\t"$15}' "source/${BIOGRID_SOURCE}.tab3.txt" | sed 's/\PUBMED://g' > biogrid.tsv
# replace first line with header line
sed -i "1s/.*/$FIRST_LINE/" biogrid.tsv
python3 convert_genesymbol_to_entrezid.py --input "biogrid.tsv" --output "biogrid.tsv" --database "source/genesymbol_to_entrezid_query_database.csv"

# IID Source File:
IID_SOURCE="human_annotated_PPIs.txt"
if [[ ! -f "source/${IID_SOURCE}" ]]; then
    if [[ ! -f "source/${IID_SOURCE}.gz" ]]; then
	    wget -O "source/${IID_SOURCE}.gz" "http://iid.ophid.utoronto.ca/static/download/${IID_SOURCE}.gz"
    fi
    cd "source/"
    gzip -d "${IID_SOURCE}.gz"
    cd "../"
    rm "source/${IID_SOURCE}.gz"
fi
awk -F "\t" '{print $1"\t"$2"\t"$3"\t"$4"\t"$6}' "source/${IID_SOURCE}" > iid.tsv
# replace first line with header line
sed -i "1s/.*/$FIRST_LINE/" iid.tsv
python3 convert_genesymbol_to_entrezid.py --input "iid.tsv" --output "iid.tsv" --database "source/genesymbol_to_entrezid_query_database.csv"

# RegNetwork Source File (+CRLF to LF conversion):
if [[ ! -f "source/human.source" ]]; then
    if [[ ! -f "source/regnetwork.zip" ]]; then
	    wget -O "source/regnetwork.zip" "http://www.regnetworkweb.org/download/human.zip"    
    fi
    unzip "source/regnetwork.zip" -d "source/"
    rm "source/regnetwork.zip"
fi
sed $'s/\r$//' "source/human.source" | awk -F "\t" '{sub(/\\n$/,"",$4);print $2"\t"$4"\t"$1"\t"$3"\t-"}' | sed 's/MIMAT/7773776584/g' | sed 's/MI/7773/g' > regnetwork.tsv 
# insert the header line
sed -i "1i $FIRST_LINE" regnetwork.tsv
python3 convert_genesymbol_to_entrezid.py --input "regnetwork.tsv" --output "regnetwork.tsv" --database "source/genesymbol_to_entrezid_query_database.csv"


# HTRiDB Source File:
if [[ ! -f "source/htridb.csv" ]]; then
    if [[ ! -f "source/htridb.csv" ]]; then
	    wget -O "source/htridb.csv" "http://www.lbbc.ibb.unesp.br/htri/consulta?type=1&all=true&down=3&iconss1.x=61&iconss1.y=61"
    fi
fi
#TODO correct this awk command
sed $'s/\r$//' "source/htridb.csv" | awk -F "\t" '{sub(/\\n$/,"",$4);print $2"\t"$4"\t"$1"\t"$3"\t-"}' > htridb.tsv
# insert the header line
sed -i "1i $FIRST_LINE" htridb.tsv
python3 convert_genesymbol_to_entrezid.py --input "htridb.tsv" --output "htridb.tsv" --database "source/genesymbol_to_entrezid_query_database.csv"
