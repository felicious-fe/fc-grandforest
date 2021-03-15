#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.supervised.R expression_data_filepath interaction_network_filepath number_of_trees seed dependent.variable.name dependent.variable.type result_forest.RData

suppressPackageStartupMessages({
  require(dplyr)
  require(grandforest)
})

args <- commandArgs(trailingOnly=TRUE)

expression_data_file <- args[1]
interaction_network_file <- args[2]
num.trees <- as.numeric(args[3])
seed <- args[4]
dependent.variable.name <- args[5]
dependent.variable.type <- args[6]
output_file <- args[7]

if(seed == "None") {
  seed <- NULL
} else {
  seed <- as.numeric(seed)
}

print('[R] Loading data from RData files')

load(interaction_network_file)
interaction_network <- data
data <- NULL

load(expression_data_file)
expression_data <- data
data <- NULL

# Remove all Variables from expression_data that are not in the interaction network
variable.names <- intersect(colnames(expression_data), unique(c(interaction_network[[1]], interaction_network[[2]], dependent.variable.name)))
expression_data <- select(expression_data, all_of(variable.names))

if(nrow(expression_data) < 2) {
  print('[R] Error: The expression data frame is too small.')
  print(colnames(expression_data))
  print('[R] Error: Check if your interaction network uses the same variables or supply a higher dimensional expression data set.')
  stop("expression data frame too small")
}

# Convert dependent variable column to factor if a classification forest is used
if(dependent.variable.type == "classification") {
  expression_data[[dependent.variable.name]] <- as.factor(expression_data[[dependent.variable.name]])
}

print(dependent.variable.type)
str(interaction_network)
str(expression_data)

print('[R] Executing GrandForest supervised')
model <- grandforest(data=expression_data,
                     graph_data=interaction_network,
                     dependent.variable.name=dependent.variable.name,
                     num.trees=num.trees,
                     seed=seed)

print('[R] Saving model to RData file')
save(model, file=output_file)

print('[R] Done')
