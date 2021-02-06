#!/usr/bin/Rscript

# Execute with args:
# grandforest.read_data_frame.R input_filepath separator output_filepath

library(readr)

args <- commandArgs(trailingOnly=TRUE)

input_filepath <- args[1]
separator <- args[2]
output_filepath <- args[3]

data <- data.frame(read_delim(input_filepath, delim=separator))

save(data, file=output_filepath)
