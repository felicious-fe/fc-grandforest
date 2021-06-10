Graph-Guided Random Forest FeatureCloud Application
============

A Graph-Guided Random Forest Algorithm for classification, regression, survival analysis and endophenotyping

## Introduction

The Application executes GrandForest, a graph-guided random forest algorithm for discovering endophenotypes and gene modules, on multiple clients and aggregates the learned information in one model. It trains a forest of decision trees on a data set and uses a provided interaction network to select feature sets for the trees, so only biologically relevant correlations are learned. The resulting model can be read as an RData file into an interactive or scripted R environment to run predictions on new data sets with the R package [grandforest](https://github.com/SimonLarsen/grandforest). Additionally, the application outputs a list of genes involved in the training and their feature importances aggregated over all clients. These feature importances can then be aggregated into a gene module or endophenotype and used as a basis for further research into the causes of the disease under investigation. Common applications are drug discovery and creating a gene panel to detect hereditary diseases and various cancer types.

The Application uses the Federated Grand Forest [federated-grandforest-R](https://github.com/felicious-fe/federated-grandforest-R) R package.

## Installation

To build the latest development version of the application as Docker image run:

```bash
git clone https://github.com/felicious-fe/fc_grandforest
cd fc_grandforest
./build.sh
```

## Reporting bugs

If you find any bugs, or if you experience any crashes, please report them at <https://github.com/felicious-fe/fc_grandforest>.
