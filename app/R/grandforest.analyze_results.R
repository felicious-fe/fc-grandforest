#!/usr/bin/Rscript

# Execute with args:
# grandforest.analyze_results.R input_model.RData interaction_network.RData output_directory_path

library(tidyverse)
library(org.Hs.eg.db)
library(grandforest)
library(geomnet)


get_top25 <- function(model) {
  top25 <- importance(model) %>%
    sort(decreasing=TRUE) %>%
    head(25)

  top25_matr <- t(as_tibble(lapply(top25, type.convert)))
  colnames(top25_matr) <- c("importance")
  top25_df <- as_tibble(top25_matr)
  top25_df$gene <- rownames(top25_matr)
  top25_df <- top25_df %>% mutate(label=mapIds(org.Hs.eg.db, gene, "SYMBOL", "ENTREZID"))
  return(top25_df)
}


plot_top25_importances <- function(top25) {
  ggplot(top25, aes(reorder(label, -importance), importance)) +
    geom_bar(stat="identity") +
    theme(axis.text.x=element_text(angle=45, hjust=1)) +
    labs(x="gene", y="importance")
}

plot_top25_subnetwork <- function(top25, network) {
  subnetwork <- filter(interaction_network, gene1 %in% top25$gene & gene2 %in% top25$gene)
  subnetwork <- as.edgedf(subnetwork)
  net.df <- fortify(subnetwork, top25[ , c("gene", "label", "importance")])

  ggplot(net.df, aes(from_id=from_id, to_id=to_id)) +
    geom_net(aes(colour=importance, label=label),
             directed=FALSE, vjust = -0.8
    ) + theme_net()
}

args <- commandArgs(trailingOnly=TRUE)

forest_input_file <- args[1]
interaction_network_file <- args[2]
output_dir <- args[3]

print('[R] Loading data from RData files')
load(interaction_network_file)
interaction_network <- data
data <- NULL

load(forest_input_file)

print('[R] Generating plots')
top25 <- get_top25(model)
plot1 <- plot_top25_importances(top25)
ggsave(filename='feature_importances.svg', device=svg(), path=output_dir)
interaction_network <- interaction_network %>%
  mutate(across(everything(), as.character))
plot_top25_subnetwork(top25, interaction_network)
ggsave(filename='interaction_subnetwork.svg', device=svg(), path=output_dir)

print('[R] Done')
