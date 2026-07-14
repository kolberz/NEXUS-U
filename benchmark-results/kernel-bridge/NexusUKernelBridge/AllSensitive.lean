/--
NEXUS-U v2.4 kernel-bridge theorem.

Scope: deterministic path certificates over finite Boolean inputs.
This theorem is deliberately generic. It proves that if every input coordinate is
sensitive at a witness and a deterministic path certificate is exact for all inputs
agreeing on its queried coordinates, then every coordinate was queried.

It does not prove the open offline multitape-Turing-machine Omega(n log n) lower bound.
-/
namespace NexusU.KernelBridge

abbrev BitInput (m : Nat) := Fin m → Bool

/-- Every coordinate selected by `queried` has value `true`. -/
def AllQueried {m : Nat} (queried : Fin m → Bool) : Prop :=
  ∀ i, queried i = true

/-- Coordinate `i` is sensitive at `x` if changing only `i` can change the output. -/
def SensitiveAt {m : Nat} {α : Type}
    (f : BitInput m → α) (x : BitInput m) (i : Fin m) : Prop :=
  ∃ y, (∀ j, j ≠ i → y j = x j) ∧ f y ≠ f x

/--
An exact deterministic path cannot omit a coordinate that is sensitive at the
witness: the sensitivity witness would preserve every queried answer, force the
same leaf/output, and contradict exactness.
-/
theorem allSensitive_forces_allQueried
    {m : Nat} {α : Type}
    (f : BitInput m → α)
    (x : BitInput m)
    (queried : Fin m → Bool)
    (pathExact : ∀ y, (∀ i, queried i = true → y i = x i) → f y = f x)
    (allSensitive : ∀ i, SensitiveAt f x i) :
    AllQueried queried := by
  intro i
  by_contra hNotQueried
  obtain ⟨y, hSame, hDifferent⟩ := allSensitive i
  apply hDifferent
  apply pathExact y
  intro j hQueried
  apply hSame j
  intro hEq
  subst j
  exact hNotQueried hQueried

/--
Conditional multiplication-facing specialization. A separate proof must establish
that the selected multiplication encoding is sensitive in all `2*n` coordinates.
-/
theorem exactMultiplicationPath_queriesEveryBit
    {n : Nat}
    (mulOutput : BitInput (2 * n) → Nat)
    (witness : BitInput (2 * n))
    (queried : Fin (2 * n) → Bool)
    (pathExact : ∀ y, (∀ i, queried i = true → y i = witness i) →
      mulOutput y = mulOutput witness)
    (allSensitive : ∀ i, SensitiveAt mulOutput witness i) :
    AllQueried queried :=
  allSensitive_forces_allQueried mulOutput witness queried pathExact allSensitive

end NexusU.KernelBridge
