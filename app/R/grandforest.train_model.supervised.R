#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.supervised.R expression_data_filepath interaction_network_filepath number_of_trees seed treetype dependent.variable.name survival.event.name survival.time.name result_forest.RData

suppressPackageStartupMessages({
  require(dplyr)
  require(grandforest)
})

args <- commandArgs(trailingOnly=TRUE)

expression_data_file <- args[1]
interaction_network_file <- args[2]
num.trees <- as.numeric(args[3])
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

load(interaction_network_file)
interaction_network <- data
data <- NULL

load(expression_data_file)
expression_data <- data
data <- NULL

print('[R] Preparing data')

if(treetype %in% c("classification", "regression", "probability")) {
  required.columns <- c(dependent.variable.name)
} else {
  required.columns <- c(survival.event.name, survival.time.name)
}

# Remove all Variables from expression_data that are not in the interaction network
variable.names <- intersect(colnames(expression_data), unique(c(interaction_network[[1]], interaction_network[[2]], required.columns)))
expression_data <- dplyr::select(expression_data, all_of(variable.names))

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

print('[R] Executing GrandForest supervised')
if(treetype %in% c("classification", "regression", "probability")) {
  model <- grandforest(data=expression_data,
                       graph_data=interaction_network,
                       dependent.variable.name=dependent.variable.name,
                       num.trees=num.trees,
                       seed=seed)
} else {
  model <- grandforest(data=expression_data,
                       graph_data=interaction_network,
                       dependent.variable.name=survival.time.name,
                       status.variable.name=survival.event.name,
                       num.trees=num.trees,
                       seed=seed)
}


print('[R] Saving model to RData file')
save(model, file=output_file)

print('[R] Done')
