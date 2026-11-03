import Lean
import Proof

-- Check the intended statement, then inspect the proof's transitive assumptions.
example : Demo.Claim := Demo.result

run_cmd do
  let allowed := #[`propext, `Quot.sound, `Classical.choice]
  let axioms ← Lean.collectAxioms `Demo.result
  for axiomName in axioms do
    unless allowed.contains axiomName do
      throwError "UNPERMITTED_AXIOM: {axiomName}"
