#!/usr/bin/Rscript

# Execute with args:
# grandforest.analyze_results.R input_model.RData interaction_network.RData expression_data.RData survival.event.name survival.time.name output_directory_path

# Analyzes the Results of a GrandForest Workflow. Creates 4*2 Plots in SVG and PNG and a TSV file with all feature importances.

suppressPackageStartupMessages({
  require(tidyverse)
  require(org.Hs.eg.db)
  require(grandforest)
  require(geomnet)
  require(ComplexHeatmap)
  require(survival)
  require(survminer)
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


plot_top25_subnetwork <- function(top25, interaction_network) {
  colnames(interaction_network) <- c("gene1", "gene2")
  subnetwork <- filter(interaction_network, gene1 %in% top25$entrez_id & gene2 %in% top25$entrez_id)
  subnetwork <- as.edgedf(subnetwork)
  net.df <- fortify(subnetwork, top25[ , c("entrez_id", "gene_symbol", "importance")])

  ggplot(net.df, aes(from_id=from_id, to_id=to_id)) +
    geom_net(aes(colour=importance, label=gene_symbol),
             directed=FALSE, vjust = -0.8
    ) + theme_net()
}


plot_patient_clustering_heatmap <- function(expression_data_scaled, clusters) {
  Heatmap(expression_data_scaled, split = clusters, name = "expression")
}


plot_patient_clustering_survival <- function(clusters, survival.event.name, survival.time.name) {
  survival_clusters <- data.frame(survival, cluster=clusters)
  ggsurvplot(survfit(Surv(survival.event.name, survival.time.name)~cluster, data=survival_clusters), pval=TRUE)$plot
}



args <- commandArgs(trailingOnly=TRUE)

forest_input_file <- args[1]
interaction_network_file <- args[2]
expression_data_file <- args[3]
survival.event.name <- args[4]
survival.time.name <- args[5]
output_dir <- args[6]


print('[R] Loading data from RData files')
load(interaction_network_file)
interaction_network <- data
data <- NULL

load(expression_data_file)
expression_data <- data
data <- NULL

load(forest_input_file)

print('[R] Generating summary')
interaction_network <- interaction_network %>%
  mutate(across(everything(), as.character))

feature_importances_df <- feature_importances_dataframe(model)
write_delim(feature_importances_df, paste(output_dir, "/feature_importances.tsv", sep=""), delim="\t")

print('[R] Clustering Patients')
top25 <- feature_importances_df %>%
  head(25) %>%
  mutate_if(is.factor, as.character)

expression_data <- as_tibble(expression_data) %>% dplyr::select(top25$entrez_id)
colnames(expression_data) <- as.character(mapIds(org.Hs.eg.db, colnames(expression_data), "SYMBOL", "ENTREZID"))
print('[R] Scaling Expression Data')
expression_data_scaled <- scale(expression_data, center=TRUE, scale=TRUE)

# Drop NA Columns (because of variance == 0 while scaling)
expression_data_scaled <- as_tibble(expression_data_scaled) %>%
  dplyr::select(where(~!all(is.na(.x))))

expression_data_scaled <- as.matrix(expression_data_scaled)

kmeans_clustering <- kmeans(expression_data_scaled, centers=2, nstart=20)
clusters <- kmeans_clustering$cluster

print('[R] Generating plots')
plot1 <- plot_top25_importances(top25)
ggsave(plot=plot1, filename='feature_importances.svg', device=svg(), path=output_dir)
ggsave(plot=plot1, filename='feature_importances.png', device=png(), path=output_dir)

plot2 <- plot_top25_subnetwork(top25, interaction_network)
ggsave(plot=plot2, filename='interaction_subnetwork.svg', device=svg(), path=output_dir)
ggsave(plot=plot2, filename='interaction_subnetwork.png', device=png(), path=output_dir)

plot3 <- plot_patient_clustering_heatmap(expression_data_scaled, clusters)
svg(paste(output_dir, 'patient_clustering_heatmap.svg', sep=""))
plot3
dev.off()
png(paste(output_dir, 'patient_clustering_heatmap.png', sep=""))
plot3
dev.off()

if (survival.event.name != 'None' & survival.time.name != 'None') {
  plot4 <- plot_patient_clustering_survival(clusters)
  ggsave(plot=plot4, filename='patient_clustering_survival.svg', device=svg(), path=output_dir)
  ggsave(plot=plot4, filename='patient_clustering_survival.png', device=png(), path=output_dir)
}

print('[R] Done')
