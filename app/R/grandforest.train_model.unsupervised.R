#!/usr/bin/Rscript

# Execute with args:
# grandforest.train_model.unsupervised.R expression_data_filepath interaction_network_filepath number_of_trees seed result_forest.RData

suppressPackageStartupMessages({
  require(dplyr)
  require(grandforest)
})

args <- commandArgs(trailingOnly=TRUE)

interaction_network_file <- args[2]
expression_data_file <- args[1]
num.trees <- as.numeric(args[3])
seed <- args[4]
output_file <- args[5]

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
<<<<<<< Updated upstream
variable.names <- intersect(colnames(expression_data), unique(c(interaction_network[[1]], interaction_network[[2]])))
=======
variable.names <- intersect(colnames(expression_data), unique(c(interaction_network[[1]], interaction_network[[2]], required.columns)))
>>>>>>> Stashed changes
expression_data <- dplyr::select(expression_data, all_of(variable.names))

if(nrow(expression_data) < 2) {
  print('[R] Error: The expression data frame is too small.')
  print(colnames(expression_data))
  print('[R] Error: Check if your interaction network uses the same variables or supply a higher dimensional expression data set.')
  stop("expression data frame too small")
}

str(interaction_network)
str(expression_data)

print('[R] Executing GrandForest unsupervised')

model <- grandforest_unsupervised(data=expression_data,
                                  graph_data=interaction_network,
                                  num.trees=num.trees,
                                  seed=seed)

print('[R] Saving model to RData file')
save(model, file=output_file)

print('[R] Done')
