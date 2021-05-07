#!/usr/bin/Rscript

# Execute with args:
# ranger.train_model.R expression_data_filepath number_of_trees minimal_node_size seed treetype dependent.variable.name survival.event.name survival.time.name result_forest.RData

# Trains a ranger model, this script is only for testing purposes.

suppressPackageStartupMessages({
  require(dplyr)
  require(ranger)
})

args <- commandArgs(trailingOnly=TRUE)

expression_data_file <- args[1]
num.trees <- as.numeric(args[2])
min.node.size <- as.numeric(args[3])
seed <- args[4]
treetype <- args[5]
dependent.variable.name <- args[6]
survival.event.name <- args[7]
survival.time.name <- args[8]
output_file <- args[9]

if(seed == "None") {
  seed <- NULL
} else {
  seed <- as.numeric(seed)
}

print('[R] Loading data from RData files')

load(expression_data_file)
expression_data <- data
data <- NULL

print('[R] Preparing data')

if(nrow(expression_data) < 2) {
  print('[R] Error: The expression data frame is too small.')
  print(colnames(expression_data))
  print('[R] Error: Check if your interaction network uses the same variables or supply a higher dimensional expression data set.')
  stop("expression data frame too small")
}

# Convert dependent variable column to factor if a classification forest is used
if(treetype == "classification") {
  expression_data[[dependent.variable.name]] <- as.factor(dplyr::pull(expression_data, dependent.variable.name))
} else if(treetype == "regression") {
  expression_data[[dependent.variable.name]] <- as.numeric(dplyr::pull(expression_data, dependent.variable.name))
} else if(treetype == "survival") {
  expression_data[[survival.event.name]] <- as.numeric(dplyr::pull(expression_data, survival.event.name))
  expression_data[[survival.time.name]] <- as.numeric(dplyr::pull(expression_data, survival.time.name))
}

print('[R] Executing Ranger RandomForest')
if(treetype %in% c("classification", "regression", "probability")) {
  model <- ranger(data=expression_data,
                  dependent.variable.name=dependent.variable.name,
                  num.trees=num.trees,
                  min.node.size=min.node.size,
                  seed=seed)
} else {
  model <- ranger(data=expression_data,
                  dependent.variable.name=survival.time.name,
                  status.variable.name=survival.event.name,
                  num.trees=num.trees,
                  min.node.size=min.node.size,
                  seed=seed)
}


print('[R] Saving model to RData file')
save(model, file=output_file)

print('[R] Done')
