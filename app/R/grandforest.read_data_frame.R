#!/usr/bin/Rscript

# Execute with args:
# grandforest.read_data_frame.R input_filepath separator output_filepath

library(readr)

args <- commandArgs(trailingOnly=TRUE)

input_filepath <- args[1]
separator <- args[2]
output_filepath <- args[3]

print('[R] Parsing data from csv file')
data <- data.frame(read_delim(input_filepath, delim=separator))
str(data)

print('[R] Saving data to RData file')
save(data, file=output_filepath)

print('[R] Done')
