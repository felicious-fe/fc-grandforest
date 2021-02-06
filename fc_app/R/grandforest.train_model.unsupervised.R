#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.unsupervised.R expressionDataFilepath interactionNetworkFilepath resultForest.RData

library(grandforest)

grandforest_unsupervised(data=data,
                         graph_data=network,
                         num.trees=10000)