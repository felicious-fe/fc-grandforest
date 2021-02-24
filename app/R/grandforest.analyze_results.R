#!/usr/bin/Rscript

# Execute with args:
# grandforest.analyze_results.R input_model.RData interaction_network.RData output_directory_path

library(tidyverse)
library(org.Hs.eg.db)
library(grandforest)
library(geomnet)


get_top25 <- function(model) {
  top25 <- importance(federated.models[[1]]) %>%
    sort(decreasing=TRUE) %>%
    head(25)

  top25_matr <- t(as_tibble(lapply(top25, type.convert)))
  colnames(top25_matr) <- c("importance")
  top25_df <- as_tibble(top25_matr)
  top25_df$gene <- rownames(top25_matr)
  top25_df <- top25_df %>% mutate(label=mapIds(org.Hs.eg.db, gene, "SYMBOL", "ENTREZID"))
  return(top25_df)
}


plot_top25_importances <- function(top25, filename) {
  postscript(paste(filename, '.pdf', sep=""), width=4, height=4)
  ggplot(top25, aes(reorder(label, -importance), importance)) +
    geom_bar(stat="identity") +
    theme(axis.text.x=element_text(angle=45, hjust=1)) +
    labs(x="gene", y="importance")
  dev.off()
}

plot_top25_subnetwork <- function(top25, network, filename) {
  subnetwork <- filter(network, gene1 %in% top25$gene & gene2 %in% top25$gene)
  subnetwork <- data.frame(label1=mapIds(org.Hs.eg.db, subnetwork$gene1, "SYMBOL", "ENTREZID"),
                           label2=mapIds(org.Hs.eg.db, subnetwork$gene2, "SYMBOL", "ENTREZID"))
  net.df <- fortify(as.edgedf(subnetwork), label=top25$label, importance=top25$importance)

  postscript(paste(filename, '.pdf', sep=""), width=4, height=4)
  ggplot(net.df, aes(from_id=from_id, to_id=to_id)) +
  geom_net(aes(colour=importance, label=from_id),
           layout.alg = "circle", directed=FALSE, size = 15,
           labelon = TRUE, labelcolour="white", vjust = 0.5, fontsize=3
  ) +
  theme_net()
  dev.off()
}

args <- commandArgs(trailingOnly=TRUE)

forest_input_file <- args[1]
interaction_network_file <- args[2]
output_dir <- args[3]

print('[R] Loading data from RData files')
load(interaction_network_file)
interaction_network <- data
data <- NULL
str(interaction_network)

load(forest_input_file)
str(model)

print('[R] Generating plots')
top25 <- get_top25(model)
plot_top25_importances(top25, paste(output_dir, '/', 'feature_importances', sep=""))
plot_top25_subnetwork(top25, interaction_network, paste(output_dir, '/', 'interaction_subnetwork', sep=""))

print('[R] Done')
