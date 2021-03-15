#!/usr/bin/Rscript

# Execute with args:
# grandforest.analyze_results.R input_model.RData interaction_network.RData output_directory_path

suppressPackageStartupMessages({
  require(tidyverse)
  require(org.Hs.eg.db)
  require(grandforest)
  require(geomnet)
})

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


feature_importances_dataframe <- function(model) {
  importance_list <- model$variable.importance %>% sort(decreasing=TRUE)
  entrezids <- as.character(names(importance_list))
  df <- data.frame(gene_symbol=as.character(mapIds(org.Hs.eg.db, entrezids, "SYMBOL", "ENTREZID")), entrez_id=entrezids, importance=importance_list)
  rownames(df) <- NULL
  return(df)
}


plot_top25_importances <- function(top25) {
  ggplot(top25, aes(reorder(gene_symbol, -importance), importance)) +
    geom_bar(stat="identity") +
    theme(axis.text.x=element_text(angle=45, hjust=1)) +
    labs(x="gene", y="importance")
}

plot_top25_subnetwork <- function(top25, network) {
  colnames(interaction_network) <- c("gene1", "gene2")
  subnetwork <- filter(interaction_network, gene1 %in% top25$entrez_id & gene2 %in% top25$entrez_id)
  subnetwork <- as.edgedf(subnetwork)
  net.df <- fortify(subnetwork, top25[ , c("entrez_id", "gene_symbol", "importance")])

  ggplot(net.df, aes(from_id=from_id, to_id=to_id)) +
    geom_net(aes(colour=importance, label=gene_symbol),
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

print('[R] Generating summary')
interaction_network <- interaction_network %>%
  mutate(across(everything(), as.character))

feature_importances_df <- feature_importances_dataframe(model)
write_delim(feature_importances_df, paste(output_dir, "/feature_importances.tsv", sep=""), delim="\t")

print('[R] Generating plots')
top25 <- feature_importances_df %>% head(25) %>% mutate_if(is.factor, as.character)
plot1 <- plot_top25_importances(top25)
ggsave(filename='feature_importances.svg', device=svg(), path=output_dir)
plot2 <- plot_top25_subnetwork(top25, interaction_network)
ggsave(filename='interaction_subnetwork.svg', device=svg(), path=output_dir)

print('[R] Done')
