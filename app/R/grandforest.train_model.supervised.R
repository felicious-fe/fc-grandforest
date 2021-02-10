#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.unsupervised.R expression_data_filepath interaction_network_filepath number_of_trees dependent.variable.name result_forest.RData

library(grandforest)
library(readr)

args <- commandArgs(trailingOnly=TRUE)

interaction_network_file <- args[2]
expression_data_file <- args[1]
num.trees <- as.numeric(args[3])
dependent.variable.name <- args[4]
output_file <- args[5]

load(interaction_network_file)
interaction_network <- data
data <- NULL

load(expression_data_file)
expression_data <- data
data <- NULL


model <- grandforest(data=expression_data[,-1],
                     graph_data=interaction_network,
                     dependent.variable.name=dependent.variable.name,
                     num.trees=num.trees)

save(model, file=output_file)
