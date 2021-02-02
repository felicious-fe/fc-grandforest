library(grandforest)
library(forcats)


grandforest.sum_models <- function(model_1, model_2) {
  if(model_1$num.independent.variables != model_2$num.independent.variables || 
     model_1$importance.mode != model_2$importance.mode ||
     model_1$treetype != model_2$treetype) {
    stop("these models cannot be summed")
  }
  
  combined.forest <- list()
  combined.forest$dependent.varID <- model_1$forest$dependent.varID
  combined.forest$num.trees <- model_1$num.trees + model_2$num.trees
  combined.forest$child.nodeIDs <- c(model_1$forest$child.nodeIDs, model_2$forest$child.nodeIDs)
  combined.forest$split.varIDs <- c(model_1$forest$split.varIDs, model_2$forest$split.varIDs)
  combined.forest$split.values <- c(model_1$forest$split.values, model_2$forest$split.values)
  combined.forest$is.ordered <- model_1$forest$is.ordered
  combined.forest$independent.variable.names <- model_1$forest$independent.variable.names
  combined.forest$treetype <- model_1$forest$treetype
  
  if(model_1$treetype == "Classification") {
    combined.forest$class.values <- model_1$forest$class.values
    combined.forest$levels <- model_1$forest$levels
  } else if(model_1$treetype == "Survival") {
    #TODO: combined.forest$child.nodeIDs und combined.forest$chf auf unique.death.times anpassen
    unique.death.times_factor <- fct_c(factor(model_1$forest$unique.death.times), factor(model_2$forest$unique.death.times))
    unique.death.times_double <- lapply(unique.death.times_factor, function (x) as.double(as.character(x)))
    combined.forest$unique.death.times <- unlist(unique.death.times_double)
    combined.forest$chf <- c(model_1$forest$chf, model_2$forest$chf)
  } else if(model_1$treetype == "Regression") {
    # Nothing more needed
  } else {
    stop("Not Implemented yet.")
  }
  
  class(combined.forest) <- "grandforest.forest"
  
  combined.model <- list()
  combined.model$num.trees = combined.forest$num.trees
  combined.model$importance.mode = model_1$importance.mode
  combined.model$treetype = model_1$treetype
  combined.model$num.independent.variables = model_1$num.independent.variables
  combined.model$forest = combined.forest
  class(combined.model) <- "grandforest"
  return(combined.model)
}



