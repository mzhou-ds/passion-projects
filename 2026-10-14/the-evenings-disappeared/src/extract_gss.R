e <- new.env(); load("gss_all.rda", envir=e); df <- e$gss_all
want <- c("year","id","ballot","age","cohort","sex","race","educ","degree",
  "marital","divorce","childs","sibs","wrkstat","hrs1","realrinc","conrinc",
  "satfin","happy","hapmar","health","socrel","socfrend","socbar","socommun",
  "socpars","socsibs","tvhours","fair","trust","helpful","life","class",
  "attend","relig","region","size","xnorcsiz","res16","mobile16",
  "wtssall","wtssps","wtssnr","lonely","friends","wrkself","occ10","prestg10","income16")
want <- want[want %in% colnames(df)]
cat("extracting:", length(want), "vars\n")
sub <- df[, want, drop=FALSE]
for (v in c("socfrend","socrel","socbar","happy","marital")) {
  cat("==", v, "==\n"); print(table(sub[[v]], useNA="ifany"))
}
write.csv(sub, "gss_extract.csv", row.names=FALSE, na="")
cat("rows:", nrow(sub), "\n")
