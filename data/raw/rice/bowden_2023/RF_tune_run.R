require(pacman)
p_load('tidyverse', 'randomForest', 'tidymodels', 'ALEPlot',
       'ggpubr', 'gridExtra', 'pdp')

# Working directory must contain two sub-directories: 'vars' and 'plots'
# set your own working directory by changing the value of 'wd' variable below:
wd <- 'D:/Users/Chris/DropBox/Dropbox (The University of Manchester)/Manchester PhD/Paper_1/sci_rep_submission/test_code_dir'
setwd(wd)

# 'vars' subdirectory must contain 'sample_data' R variable
# sample_data contains 1980 - 1984 data for quick+easy running of code below
load('vars/sample_data')

# 1. Tuning for each response model ######
# Wrapper function for tuning models
#
#
# INPUT ARGUMENTS:
# # input_data: production and weather variables in the format of sample_data  
# # response_list: list any of: dt_norm_rice_yield_kgha, dt_norm_rice_area_kha, dt_norm_rice_prod_kt
# # pred_list: list any of: mean_tmin, mean_tmax, agdd, dswrf_sum, total_p, rainy_prop, onset_allYears_dev, rice_irri_prop, season_length
#
#
# OUTPUT:
# # named list of tibbles, one tibble per response variable specified in response_list
# # tibble presents tuning results with three columns: mtry // OOBError // ntrees
tuningWrapper <- function(input_data, response_list, pred_list){

  tidyModelsTune <- function(data_in, response_var, seed, formula, pred_list){

    # Set seed
    set.seed(seed)

    # Split data into train and test sets
    split_set <- initial_split(input_data, prop = 0.75)
    train_set <- training(split_set)
    test_set <- testing(split_set)

    # Pre-requisite steps for tidymodels tuning function
    model_recipe <- recipe(as.formula(formula), data = train_set)
    model_prep <- prep(model_recipe)
    model_juiced <- juice(model_prep)

    # use tidymodels to tune ntrees parameter first
    tune_spec <- rand_forest(
      mtry = 3, # default value (number of predictors/3)
      trees = tune(),
      min_n = 5 # default value for all regression RFs
    ) %>%
      set_mode('regression') %>%
      set_engine('randomForest')

    # combine recipe and tuning specification into a tidymodels workflow
    tune_workflow <- workflow() %>%
      add_recipe(model_recipe) %>%
      add_model(tune_spec)

    # create cross-validation set
    model_folds <- vfold_cv(train_set)

    # speed up process using parallelisation
    doParallel::registerDoParallel(cores = 2)

    # set appropriate range of grid values
    rf_grid <- grid_regular(
      trees(range = c(400, 1000)), levels = 7
    )

    # perform ntrees tuning
    ntree_results <- tune_grid(
      tune_workflow,
      resamples = model_folds,
      grid = rf_grid
    )

    # Print the response variable currently being used for tuning
    print(paste0('Tuning trees for ', response_var))

    # Plot results of ntree tuning (OOB RMSE values)
    ntree_plot <- ntree_results %>%
      collect_metrics() %>%
      filter(.metric == "rmse") %>%
      ggplot(aes(trees, mean)) +
      geom_line(alpha = 0.5, size = 1.5) +
      geom_point() +
      labs(y = "RMSE") +
      theme_classic() +
      theme(axis.title.x = element_text(size = 24),
            axis.title.y = element_text(size = 24),
            axis.text.x = element_text(size = 22),
            axis.text.y = element_text(size = 22),
            legend.text = element_text(size = 22),
            legend.title = element_text(size = 22)
      ) +
      scale_x_continuous(expand = c(0.1, .1))

    plot(ntree_plot)

    # take user input for minimium viable number of trees 
    # this will then be used for subsequent mtry tuning
    opt_ntrees <- as.numeric(readline(prompt = 'Based on the plot, enter minimum viable ntrees to be used for further tuning: '))

    # Now that ntrees tuning data has been collected, tune mtry
    res_ind <- grep(paste0('^', response_var, '$'), colnames(data_in))
    results <- as_tibble(tuneRF(x = data_in[,-res_ind],
                                y = pull(data_in, !! response_var),
                                stepFactor = 1.5,
                                mtryStart = 2,
                                ntreeTry = opt_ntrees,
                                improve = 0.01))

    # add ntrees tuning result to 'results' output
    results[['ntrees']] <- opt_ntrees

    return(results)

  }

  tune_results <- list()

  # perform custom tuning function (tidyModelsTune) on each response variable provided by user
  for(each_response in response_list){

    # create RF formulas for tuning purposes
    preds_form <- paste(pred_list, collapse = ' + ')
    each_formula <- paste0(each_response, ' ~ ', preds_form)

    # filter input data to only include each response variable
    flt_data <- input_data %>%
      select(!! pred_list, !! each_response)

    # run custom tuning function
    response_res <- tidyModelsTune(flt_data, each_response,
                                   seed = 1,
                                   formula = each_formula)

    # store tuning output
    tune_results[[each_response]] <- response_res

  }

  return(tune_results)

}

# basic predictor variables for creating models for tuning
rf_vars <- c(
  'mean_tmin', 'mean_tmax', 'agdd', 'dswrf_sum', 'total_p', 'rainy_prop',
  'onset_allYears_dev', 'rice_irri_prop', 'season_length'
)

# main tuning wrapper run
tune_results <- tuningWrapper(input_data = sample_data,
                              response_list = c('dt_norm_rice_yield_kgha'
                                                # 'dt_norm_rice_area_kha',
                                                # 'dt_norm_rice_prod_kt'
                                                ),
                              pred_list = rf_vars)

#
# 2. Modelling runs (100) for each response variable and plotting ####
multiRunWrapper <- function(input_data, response_list, pred_vars, mtry_in, ntree_in){

  # sub-function for running a single RF model
  runRfModel <- function(input_data, var_list, formula_input, seed_in,
                         mtry_in, ntree_in){

    set.seed(seed_in)

    # perform randomForest run, measure variable importance
    rf_output <- randomForest(formula = as.formula(formula_input),
                              data = input_data,
                              importance = T,
                              mtry = mtry_in,
                              ntree = ntree_in)

    return(rf_output)

  }

  # sub-function which calls 'runRfModel' and returns outputs from multiple runs
  manyRfRuns <- function(seed_input, reps,
                         rf_input, rf_var_list, rf_formula,
                         mtry_in, ntree_in){

    set.seed(seed_input)

    output_list <- list()

    # loop through number of RF run reps specified and store output in a named list
    for(i in 1:reps){

      each_rf <- runRfModel(rf_input[,c(rf_var_list)], rf_var_list, rf_formula, i,
                            mtry_in, ntree_in)

      output_list[[as.character(i)]] <- each_rf

      print(paste0('Completed run ', i, ' at ', Sys.time()))

    }

    return(output_list)

  }

  # extract variance explained and RMSE by each model in input list
  extractVar <- function(rf_list){

    var_list <- list()
    rmse_list <- list()

    for(i in 1:length(rf_list)){

      # R squared and MSE of each model are stored as vectors by randomForest
      # ...the final element in each vector is the overall model score (500 for 500 ntrees)
      each_var <- rf_list[[i]]$rsq[500]
      each_rmse <- sqrt(rf_list[[i]]$mse[500])

      var_list <- append(var_list, each_var)
      rmse_list <- append(rmse_list, each_rmse)

    }

    results <- tibble(model_no = 1:length(rf_list),
                      var_expl = unlist(var_list),
                      rmse_oob = unlist(rmse_list))

    return(results)

  }

  # extract variable importance info from each model in input list
  extractVip <- function(rf_list){

    vip_output <- tibble(tech_names = character(),
                         `%IncMSE` = numeric(),
                         `IncNodePurity` = numeric(),
                         model_id = numeric())

    for(i in 1:length(rf_list)){

      # use randomForest's importance() function to extract permutation variable importance
      vip_temp <- as.data.frame(importance(rf_list[[as.character(i)]])) %>%
        mutate(tech_names = rownames(.),
               model_id = i)

      vip_output <- bind_rows(vip_output, vip_temp)

    }

    return(vip_output)

  }

  # create a single ALE plot and return its x/y coordinates as a tibble
  createSingleAlePlot <- function(rf_data, rf_model, predictor, response_var){

    # generic prediction function required by ALE plotting function
    yhat <- function(X.model, newdata) as.numeric(predict(X.model, newdata))

    # preparing format of input data for ALE plotting function
    full_vars <- names(rf_data)
    remove_ind <- which(full_vars == response_var)
    training_rf <- rf_data[,-remove_ind]
    var_ind <- which(names(rf_data) == predictor)

    # plot ALE for each predictor
    ale_raw <- ALEPlot(X = as.data.frame(training_rf),
                       X.model = rf_model,
                       pred.fun = yhat,
                       J = var_ind)

    # store ALE x/y coordinates in a tibble for future usage (95th percentile/mean)
    ale_tbl <- tibble(x = ale_raw$x.values,
                      y = ale_raw$f.values)

    return(ale_tbl)

  }

  # extract data required for ALE plots from a list of RF models
  extractAllAleData <- function(rf_list, predictor_list, input_data, res_var){

    # calls createSingleAlePlot() and stores multiple outputs from multiple runs
    extractAle <- function(rf_list, predictor, input_data, res_var){

      ale_output <- tibble(x = numeric(),
                           y = numeric(),
                           model_id = numeric(),
                           predictor = character())

      for(i in 1:length(rf_list)){ #

        print(paste0(predictor, ' ', i))

        rf_ale_raw <- createSingleAlePlot(input_data,
                                          rf_list[[i]],
                                          predictor, res_var)

        # prep each single ALE plot's data to be joined to final output tibble
        ale_temp <- tibble(x = rf_ale_raw$x,
                           y = rf_ale_raw$y,
                           model_id = i,
                           predictor = predictor)

        ale_output <- bind_rows(ale_output, ale_temp)

      }

      return(ale_output)

    }

    final_out <- tibble(x = numeric(),
                        y = numeric(),
                        model_id = numeric(),
                        predictor = character())

    for (each_pred in predictor_list){

      # helps user keep track of which predictor is currently being extracted
      print(each_pred)
      
      # extracting ALE information from models and storing output
      ale_output <- extractAle(rf_list, each_pred, input_data, res_var = res_var)
      final_out <- bind_rows(final_out, ale_output)

    }

    return(final_out)

  }

  # interpolating ALE x/y coordinate data
  # ...this is required because each individual ALE has slightly
  # different x values. However, in order to plot mean/95th CI 
  # of 100 ALE plots, they all need to have the same set of
  # x values. 
  interpAle <- function(ale_data, predictor_list){

    interp_output <- tibble(x = numeric(),
                            y = numeric(),
                            model_id = factor(),
                            predictor = character())

    for(each_pred in predictor_list){

      # filter data to consider one predictor variable at a time
      pred_data <- filter(ale_data, predictor == each_pred)

      # gather all unique x values per predictor
      unique_xs <- unique(pred_data$x)

      model_numbers <- unique(pred_data$model_id)

      pred_output <- tibble(x = numeric(),
                            y = numeric(),
                            model_id = factor(),
                            predictor = character())

      # for each model (of 100), interpolate y values for each unique x value from above 
      for(each_model_id in model_numbers){

        model_data <- filter(pred_data, model_id == each_model_id)

        modelInterpFun <- approxfun(x = model_data$x,
                                    y = model_data$y,
                                    method = 'linear')

        interp_results <- tibble(x = unique_xs,
                                 y = modelInterpFun(unique_xs))

        model_output <- interp_results %>%
          mutate(model_id = as.factor(each_model_id),
                 predictor = each_pred)


        pred_output <- bind_rows(pred_output, model_output)

        print(paste0('Completed ', each_pred, ' model ', each_model_id, ' at ', Sys.time()))

      }

      interp_output <- bind_rows(interp_output, pred_output)

    }

    return(interp_output)

  }

  # using input data for RF, collect 98th percentile ranges for each
  # predictor variable. This is later used to limit ranges of x axes
  # in ALE plots, excluding edge effects from presentation.
  getPercentileRanges <- function(rf_data, percentile, predictor_list){

    temp <- (100 - percentile)/200 # /200 because half of (1-percentile) goes on either bound

    upper_bound <- 1 - temp
    lower_bound <- 0 + temp

    percentiles_out <- tibble(predictor = character(),
                              upper_quantile = numeric(),
                              lower_quantile = numeric())

    for(each_predictor in predictor_list){

      upper_quantile <- quantile(rf_data[[each_predictor]], upper_bound, na.rm = T)
      lower_quantile <- quantile(rf_data[[each_predictor]], lower_bound, na.rm = T)

      temp_tbl <- tibble(predictor = each_predictor,
                         upper_quantile = upper_quantile,
                         lower_quantile = lower_quantile)

      percentiles_out <- bind_rows(percentiles_out, temp_tbl)

    }

    return(percentiles_out)

  }

  # full wrapper for plotting all individual ALEs, calling all previous sub-fns
  plotIndividualAleFinal <- function(uncertainty_data, predictor_list,
                                     percentile_data, histo_type, input_data, save_path){

    # named list for easy+neat labelling of plots
    labelling <- list('total_p' = 'Total precipitation (mm)',
                      "onset_allYears_dev" = 'Onset deviation (days)',
                      "season_length" = 'Monsoon season length (days)',
                      "mean_tmin" = 'Mean minimum temperature (\u00B0C)',
                      "mean_tmax" = 'Mean maximum temperature (\u00B0C)',
                      'mean_tavg' = 'Mean average temperature (\u00B0C)',
                      "dswrf_sum" = expression('DSWRF (W / m'^'-2'*')'),
                      "mean_dry_length" = 'Mean dry spell length (days)',
                      "rice_irri_prop" = 'Irrigated area proportion',
                      'cold_days' = 'Cool nights',
                      'hot_days' = 'Warm days',
                      'wet_days' = 'Wet days',
                      'low_rad_days' = 'Low DSWRF days',
                      'agdd' = 'Growing degree days',
                      'rainy_prop' = 'Rainy days proportion')

    for(each_pred in predictor_list){

      upper_percentile <- filter(percentile_data, predictor == each_pred)$upper_quantile
      lower_percentile <- filter(percentile_data, predictor == each_pred)$lower_quantile

      pred_data <- filter(uncertainty_data, predictor == each_pred)

      raw_input <- input_data %>%
        ungroup() %>%
        filter(.data[[each_pred]] >= lower_percentile,
               .data[[each_pred]] <= upper_percentile)

      if(histo_type == 'none'){

        pred_plot <- ggplot(pred_data, aes(x = x, y = mean_avg)) +
          geom_line() +
          geom_ribbon(aes(ymin = lower025, ymax = upper975), alpha = 0.2) +
          theme_classic() +
          xlab(labelling[[each_pred]]) + ylab('ALE yield (kg/ha)') +
          geom_abline(slope = 0, intercept = 0, linetype = 'dashed') +
          coord_cartesian(xlim=c(lower_percentile, upper_percentile))

        # 'pdf' is what was exclusively used to create probability distribution fn plots for the manuscript
      } else if(histo_type == 'pdf'){

        # create histogram and store x/y coordinates
        histo <- ggplot(raw_input, aes_string(x = each_pred)) +
          geom_histogram(aes(y = stat(count / sum(count))), bins = 30)
        histo_build <- ggplot_build(histo)
        histo_probs <- dplyr::select(as.data.frame(histo_build$data), x, y)

        # scale mean and 95th percentile of ALE effects to match secondary y axis of histogram 
        a            <- range(histo_probs[['y']])
        b            <- range(pred_data$mean_avg)
        scale_factor <- diff(a)/diff(b)

        pred_data[['mean_avg2']] <- ((pred_data[['mean_avg']] - b[1]) * scale_factor) + a[1]
        pred_data[['lower025_2']] <- ((pred_data[['lower025']] - b[1]) * scale_factor) + a[1]
        pred_data[['upper975_2']] <- ((pred_data[['upper975']] - b[1]) * scale_factor) + a[1]

        trans <- ~ ((. - a[1]) / scale_factor) + b[1]
        zero_line <- a[1] - b[1] * scale_factor

        # plot ALE with a secondary y axis, applying the transformation from scaling above
        pred_plot <- ggplot() +
          geom_histogram(data = histo_probs, aes(x = x, y = y), stat = 'identity', fill='red', alpha = 0.35) +
          geom_line(data = pred_data, aes(x = x, y = mean_avg2), size = 0.8) +
          geom_ribbon(data = pred_data, aes(x = x, y = mean_avg2, ymin = lower025_2, ymax = upper975_2), size = 0.8, alpha = 0.2) +
          scale_y_continuous(name = 'Freq',
                             sec.axis = sec_axis(trans=trans,
                                                 name='ALE production (kt)')) +
          theme_classic() +
          xlab(labelling[[each_pred]]) +
          geom_abline(slope = 0, intercept = zero_line, linetype = 'dashed') +
          coord_cartesian(xlim=c(lower_percentile, upper_percentile)) +
          theme(axis.text.x = element_text(size = 18),
                axis.text.y = element_text(size = 18),
                axis.title.x = element_text(size = 18, vjust = -0.5),
                axis.title.y = element_text(size = 18),
                axis.title.y.right = element_text(vjust = 2.2))

      }


      filenaming <- list('none' = 'neat',
                         'histo' = 'histo',
                         'pdf' = 'pdf')

      save_file <- paste0(save_path, each_pred, '.png')

      ggsave(filename = save_file,
             plot = pred_plot,
             width = 20,
             height = 12,
             units = 'cm')

    }

  }

  name_convert <- list('dt_norm_rice_yield_kgha' = 'yield',
                       'dt_norm_rice_area_kha' = 'area',
                       'dt_norm_rice_prod_kt' = 'prod')

  vip_labels <- c('rice_irri_prop' = 'Irrigation proportion',
                  'dswrf_sum' = 'DSWRF Sum', 'wet_days' = 'Wet days', 'season_length' = 'Season length',
                  'total_p' = 'Total precipitation', 'cold_days' = 'Cool nights', 'hot_days' = 'Warm days',
                  'onset_allYears_dev' = 'Onset deviation', 'mean_tavg' = 'Mean average temp',
                  'low_rad_days' = 'Low DSWRF days', 'mean_tmin' = 'Mean min temp',
                  'mean_tmax' = 'Mean max temp', 'agdd' = 'Growing degree days',
                  'rainy_prop' = 'Rainy days proportion')

  vip_labels_df <- tibble(tech_names = c(names(vip_labels)),
                          label_names = c(vip_labels))

  for(each_response in response_list){

    model_vars <- append(pred_vars, each_response)

    flt_data <- input_data %>%
      select(all_of(model_vars))

    rf_runs <- manyRfRuns(seed_input = 100,
                          reps = 100,
                          rf_input = flt_data,
                          rf_var_list = colnames(flt_data),
                          rf_formula = paste0(each_response, ' ~ .'),
                          mtry_in = mtry_in,
                          ntree_in = ntree_in)

    # Get %var and OOB RMSE from all 100 runs
    perf_data <- extractVar(rf_runs)

    save(perf_data, file = paste0('plots/', name_convert[[each_response]], '_perf_data'))


    # Get variable importance (VI) data from 100 runs
    vip_data <- extractVip(rf_runs) %>%
      group_by(tech_names) %>%
      mutate(mean_incmse = mean(`%IncMSE`), # get mean and 95th percentiles for VI
             incmse_975 = quantile(`%IncMSE`, 0.975),
             incmse_025 = quantile(`%IncMSE`, 0.025)) %>%
      select(tech_names, mean_incmse, incmse_975, incmse_025) %>%
      distinct() %>%
      left_join(vip_labels_df)

    save(vip_data, file = paste0('plots/', name_convert[[each_response]], '_vip_data'))

    viplot <- ggplot(vip_data, aes(x = mean_incmse, y = reorder(label_names, mean_incmse))) +
      geom_bar(stat = 'identity') +
      geom_errorbar(aes(xmin = incmse_025, xmax = incmse_975), width = 0.2) +
      labs(x = '% mean increase in MSE', y = 'Predictor') +
      theme_classic()



    ggsave(plot = viplot, filename = paste0('plots/100_', name_convert[[each_response]], '.png'),
           height = 9, width = 16, units = 'cm')


    # Get uncertainty and percentile data from 100 runs to use in ALE plotting
    uncert_data <- rf_runs %>%
      extractAllAleData(pred_vars, flt_data, each_response) %>%
      interpAle(pred_vars) %>%
      group_by(predictor, x) %>%
      mutate(mean_avg = mean(y, na.rm = T),
             stdev = sd(y, na.rm = T),
             samplesize = length(y[!is.na(y)]),
             stderror = stdev/(sqrt(samplesize)),
             tscore = qt(p = 0.05/2, df = samplesize - 1, lower.tail = F),
             marginerror = tscore*stderror,
             upperCI = mean_avg + marginerror,
             lowerCI = mean_avg - marginerror,
             upper975 = quantile(y, 0.975, na.rm = T),
             lower025 = quantile(y, 0.025, na.rm = T))


    percentiles_98 <- getPercentileRanges(flt_data,
                                          percentile = 98,
                                          pred_vars)



    save(uncert_data, file = paste0('plots/',
                                    name_convert[[each_response]], '_uncert_data'))

    save(percentiles_98, file = paste0('plots/',
                                       name_convert[[each_response]], '_percentiles_98'))

    # Plot uncertainty-based ALEs
    ale_path <- paste0('plots/', name_convert[[each_response]], '_ale_')

    plotIndividualAleFinal(uncert_data,
                           pred_vars,
                           percentiles_98,
                           'pdf',
                           input_data = flt_data,
                           save_path = ale_path)

  }

}

pred_vars <- c(
  'mean_tmin', 'mean_tmax',
  'agdd',
  'dswrf_sum', 'total_p',
  'rainy_prop',
  'onset_allYears_dev', 'rice_irri_prop',
  'season_length'
)

multiRunWrapper(input_data = sample_data,
                response_list = c(
                  'dt_norm_rice_yield_kgha'
                  # 'dt_norm_rice_area_kha'
                ),
                pred_vars = pred_vars,
                mtry_in = 3,
                ntree_in = 500)
