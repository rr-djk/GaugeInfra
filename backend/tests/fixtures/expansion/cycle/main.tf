# Cycle de modules : a -> b -> a. Détecté via source_stack (racine résolue),
# enregistré dans unparsed_files, jamais levé.
module "a" {
  source = "./mod_a"
}
