import Lean
import Submission

-- Check the intended statement, then inspect the proof's transitive assumptions.
example : Demo.Claim := Demo.candidate

run_cmd do
  let allowed := #[`propext, `Quot.sound, `Classical.choice]
  let axioms ← Lean.collectAxioms `Demo.candidate
  for axiomName in axioms do
    unless allowed.contains axiomName do
      throwError "UNPERMITTED_AXIOM: {axiomName}"
