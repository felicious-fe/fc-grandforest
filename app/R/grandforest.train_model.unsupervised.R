#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.unsupervised.R expression_data_filepath interaction_network_filepath number_of_trees result_forest.RData

library(grandforest)

args <- commandArgs(trailingOnly=TRUE)

interaction_network <- read.csv(args[2], sep='\t')
expression_data <- data.frame(read_csv2(args[1]))
num.trees <- args[3]

model <- grandforest_unsupervised(data=expression_data,
                                  graph_data=interaction_network,
                                  num.trees=num.trees)

save(model, file=args[4])
