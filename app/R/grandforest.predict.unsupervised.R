#!/usr/bin/Rscript

# Execute with args:
# grandforest.predict.unsupervised.R input_model.RData expression_data.RData output_directory_path

suppressPackageStartupMessages({
  require(tidyverse)
  require(org.Hs.eg.db)
  require(grandforest)
})

args <- commandArgs(trailingOnly=TRUE)

forest_input_file <- args[1]
expression_data_file <- args[2]
output_dir <- args[3]

print('[R] Loading data from RData files')

load(forest_input_file)

load(expression_data_file)
expression_data <- data
data <- NULL

print('[R] Executing GrandForest prediction')
prediction <- predict(model, data=expression_data)

print('[R] Saving prediction to files')
write_delim(data.frame(Y_pred=prediction$predictions), paste(output_dir, "/", "Y_pred.tsv", sep=""), delim="\t")

print('[R] Done')
