#!/usr/bin/Rscript

# Execute with args:
# grandforest.sum_models.R firstForest.RData secondForest.RData resultForest.RData

suppressPackageStartupMessages({
  require(grandforest)
  require(forcats)
})

args <- commandArgs(trailingOnly=TRUE)

forest1_input_file <- args[1]
forest2_input_file <- args[2]
output_file <- args[3]

print('[R] Loading models from RData files')

load(forest1_input_file)
forest1 <- model
model <- NULL
str(forest1)

load(forest2_input_file)
forest2 <- model
model <- NULL
str(forest2)

print('[R] Aggregating models')
model <- grandforest_sum_models(forest1, forest2)

print('[R] Saving aggregated model to RData file')
save(model, file=output_file)

print('[R] Done')

