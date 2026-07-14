/--
NEXUS-U v2.4 formalization target.

This file declares the restricted-model definitions and the proposition to be proved.
It deliberately contains no `axiom`, `sorry`, or `admit`, and it is not labeled
kernel-verified unless an external Lean toolchain accepts a completed proof.
-/

namespace NexusU.LowerBounds

abbrev BitVector (m : Nat) := Fin m → Bool

/-- A coordinate is sensitive when flipping only that coordinate changes the output. -/
def SensitiveAt {m α : Type} [DecidableEq α]
    (f : m → α) (x : m) (flip : m → m) : Prop :=
  f x ≠ f (flip x)

/-- Formal target metadata for the decision-tree lower bound. -/
structure QueryLowerBoundTarget where
  inputBits : Nat
  claimedDepth : Nat
  exact : Bool
  deterministic : Bool

def exactMultiplicationQueryTarget (n : Nat) : QueryLowerBoundTarget := {
  inputBits := 2 * n
  claimedDepth := 2 * n
  exact := true
  deterministic := true
}

/--
The proposition below is a formalization target, not a theorem assertion.
A completed development must define deterministic adaptive bit-query trees,
execution transcripts, exactness, and worst-case depth, then prove that the
all-ones multiplication witness forces every one of the `2*n` coordinates to
be queried.
-/
def ExactMultiplicationNeedsAllBits : Prop :=
  ∀ n : Nat, 0 < n →
    (exactMultiplicationQueryTarget n).claimedDepth = 2 * n

end NexusU.LowerBounds
