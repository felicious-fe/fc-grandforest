#!/usr/bin/Rscript

# Execute with args:
# ranger.predict.R input_model.RData expression_data.RData dependent.variable.name output_directory_path

# Predicts data with a ranger model, this script is only for testing purposes.

suppressPackageStartupMessages({
  require(tidyverse)
  require(org.Hs.eg.db)
  require(ranger)
})

args <- commandArgs(trailingOnly=TRUE)

forest_input_file <- args[1]
expression_data_file <- args[2]
dependent.variable.name <- args[3]
output_dir <- args[4]

print('[R] Loading data from RData files')

load(forest_input_file)

load(expression_data_file)
expression_data <- data
data <- NULL

print('[R] Executing Ranger RandomForest prediction')
prediction <- predict(model, data=expression_data)

print('[R] Saving prediction to files')
write_delim(data.frame(Y_pred=prediction$predictions), paste(output_dir, "/", "Y_pred.tsv", sep=""), delim="\t")
write_delim(data.frame(Y_true=expression_data[[dependent.variable.name]]), paste(output_dir, "/", "Y_true.tsv", sep=""), delim="\t")

print('[R] Done')
