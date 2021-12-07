
Graph-Guided Random Forest FeatureCloud Application
============

A Graph-Guided Random Forest Algorithm for classification, regression, survival analysis and endophenotyping

## Description

The Application executes GrandForest, a graph-guided random forest algorithm for discovering endophenotypes and gene modules, on multiple clients and aggregates the learned information in one model. It trains a forest of decision trees on a data set and uses a provided interaction network to select feature sets for the trees, so only biologically relevant correlations are learned. The resulting model can be read as an RData file into an interactive or scripted R environment to run predictions on new data sets with the R package [grandforest](https://github.com/SimonLarsen/grandforest). Additionally, the application outputs a list of genes involved in the training and their feature importances aggregated over all clients. These feature importances can then be aggregated into a gene module or endophenotype and used as a basis for further research into the causes of the disease under investigation. Common applications are drug discovery and creating a gene panel to detect hereditary diseases and various cancer types.

The Application uses the Federated Grand Forest [federated-grandforest-R](https://github.com/felicious-fe/federated-grandforest-R) R package.

## Input
- `interaction_network`: biogrid, htridb, iid, regnetwork or filepath
- `expression_data`: containing the local expression data


## Output
TODO


## Workflows
Can be combined with the following apps:

Pre: Cross Validation


## Config
Use the config file to customize your training. Just upload it together with your training data as `config.yml`
```yml
fc_grandforest:
  global_options:
    grandforest_method: unsupervised  # supervised or unsupervised
    grandforest_treetype: survival  # classification, regression, survival or probability
    number_of_trees: 10000
    minimal_node_size: 3 # Helps with privacy preservation. Lower values could potentially reveal private data, values below 3 are not allowed. Values greater than 10 are considered good, but model performance suffers on small data sets.
    seed: 2021
    interaction_network: biogrid.tsv  # biogrid, htridb, iid, regnetwork or filepath
    interaction_network_separator: "\t"  # only used with filepath
  local_options:
    prediction: True  # boolean
  local_files:
    expression_data: expression_data.csv  # filepath
    expression_data_survival_event: os_event  # only used in survival
    expression_data_survival_time: os_time  # only used in survival
    expression_data_separator: ";"
  split:
    mode: file  # file or directory
    dir: . # data or .
```

## Privacy
- No raw data is exchanged with other participants. Only trained decision tress are exchanged, as well as the number of samples
- Does not implement privacy-enhancing techniques yet

## Installation

To build the latest development version of the application as Docker image run:

```bash
git clone https://github.com/felicious-fe/fc_grandforest
cd fc_grandforest
./build.sh
```

## Reporting bugs

If you find any bugs, or if you experience any crashes, please report them at <https://github.com/felicious-fe/fc_grandforest>.
