#!/usr/bin/env Rscript
# validate_vs_mada.R — Cross-validate MetaSprint DTA bivariate GLMM against R mada::reitsma()
#
# Runs reitsma() on 3 datasets with both REML (mada default) and ML estimation.
# Outputs JSON to stdout for parsing by test_r_validation.py.
#
# Usage: Rscript validate_vs_mada.R

suppressMessages(library(mada))
suppressMessages(library(jsonlite))

# --- Dataset 1: BNP for Heart Failure (k=6) ---
bnp <- data.frame(
  TP = c(52, 44, 379, 89, 40, 163),
  FP = c(14, 20, 83, 17, 22, 44),
  FN = c(8, 6, 65, 14, 5, 21),
  TN = c(76, 151, 959, 337, 138, 416)
)

# --- Dataset 2: hs-Troponin for AMI (k=5) ---
hstrop <- data.frame(
  TP = c(45, 98, 72, 33, 156),
  FP = c(12, 25, 18, 8, 40),
  FN = c(5, 10, 8, 3, 15),
  TN = c(88, 167, 102, 56, 289)
)

# --- Dataset 3: CTCA for CAD (k=4, includes fn=0 edge case) ---
ctca <- data.frame(
  TP = c(30, 65, 22, 88),
  FP = c(8, 15, 5, 22),
  FN = c(2, 5, 0, 7),
  TN = c(60, 115, 73, 183)
)

extract_results <- function(fit, dataset_name, method_name) {
  # reitsma models logit(sensitivity) and logit(FPR)
  # coefficients: tsens.(Intercept) = logit(pooled sens)
  #               tfpr.(Intercept)  = logit(pooled FPR), so spec = 1 - plogis(tfpr)

  # coef(fit) returns a matrix: row "(Intercept)", cols "tsens" and "tfpr"
  coefs <- coef(fit)
  vcov_mat <- vcov(fit)

  logit_sens <- as.numeric(coefs["(Intercept)", "tsens"])
  logit_fpr  <- as.numeric(coefs["(Intercept)", "tfpr"])

  # Standard errors from variance-covariance matrix
  se_logit_sens <- sqrt(vcov_mat["tsens.(Intercept)", "tsens.(Intercept)"])
  se_logit_fpr  <- sqrt(vcov_mat["tfpr.(Intercept)", "tfpr.(Intercept)"])

  # Pooled estimates
  pooled_sens <- plogis(logit_sens)
  pooled_fpr  <- plogis(logit_fpr)
  pooled_spec <- 1 - pooled_fpr

  # 95% CIs on logit scale, back-transformed
  z975 <- qnorm(0.975)
  sens_ci_lo <- plogis(logit_sens - z975 * se_logit_sens)
  sens_ci_hi <- plogis(logit_sens + z975 * se_logit_sens)

  # For specificity: spec = 1 - FPR, so spec CI reverses FPR CI
  fpr_ci_lo <- plogis(logit_fpr - z975 * se_logit_fpr)
  fpr_ci_hi <- plogis(logit_fpr + z975 * se_logit_fpr)
  spec_ci_lo <- 1 - fpr_ci_hi  # lower spec = higher FPR
  spec_ci_hi <- 1 - fpr_ci_lo  # higher spec = lower FPR

  # DOR = exp(logit(sens) + logit(spec))
  # logit(spec) = logit(1 - FPR) = -logit(FPR) = -logit_fpr
  logit_spec <- -logit_fpr
  dor <- exp(logit_sens + logit_spec)

  # AUC from mada
  auc_val <- tryCatch({
    auc_obj <- AUC(fit)
    as.numeric(auc_obj$AUC)
  }, error = function(e) NA_real_)

  # Tau-squared from Psi (between-study variance-covariance)
  psi <- fit$Psi
  tau2_sens <- psi[1, 1]
  tau2_fpr  <- psi[2, 2]

  list(
    dataset    = dataset_name,
    method     = method_name,
    k          = nrow(fit$data),
    logit_sens = logit_sens,
    logit_fpr  = logit_fpr,
    logit_spec = logit_spec,
    se_logit_sens = se_logit_sens,
    se_logit_fpr  = se_logit_fpr,
    pooled_sens   = pooled_sens,
    pooled_spec   = pooled_spec,
    sens_ci_lo = sens_ci_lo,
    sens_ci_hi = sens_ci_hi,
    spec_ci_lo = spec_ci_lo,
    spec_ci_hi = spec_ci_hi,
    dor        = dor,
    auc        = auc_val,
    tau2_sens  = tau2_sens,
    tau2_fpr   = tau2_fpr,
    psi_offdiag = psi[1, 2]
  )
}

# --- Run analyses ---
results <- list()

datasets <- list(
  list(data = bnp,    name = "BNP_HF_k6"),
  list(data = hstrop, name = "hsTroponin_AMI_k5"),
  list(data = ctca,   name = "CTCA_CAD_k4")
)

for (ds in datasets) {
  # REML (mada default)
  fit_reml <- reitsma(ds$data, method = "reml")
  results[[length(results) + 1]] <- extract_results(fit_reml, ds$name, "REML")

  # ML (closer to DerSimonian-Laird for comparison)
  fit_ml <- reitsma(ds$data, method = "ml")
  results[[length(results) + 1]] <- extract_results(fit_ml, ds$name, "ML")
}

# Output as JSON
json_out <- toJSON(results, auto_unbox = TRUE, digits = 10, pretty = TRUE)
cat(as.character(json_out))
