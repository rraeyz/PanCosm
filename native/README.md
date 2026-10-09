# Compiled routines

Rust code for the loops NumPy cannot do fast (plans/architecture.md ARC-9). The program runs without it:
every routine has a NumPy twin, used when the module is not built or `ASTROWB_NATIVE=off`.

Build (Rust from rustup; the version in `rust-toolchain.toml` installs itself):

    python tools/build_native.py      # puts src/astrowb/_native.* next to the package

## Adding a routine

1. Write it in `src/lib.rs` as a `#[pyfunction]`: float64 NumPy inputs, the work inside `py.detach` (the GIL
   released) and `catch_unwind` (no panic reaches Python), rayon above a size where threads pay, the same numbers
   whatever the thread count. Register it in the `#[pymodule]`.
2. Keep the Python version as the twin, and call through `native.use`:

       fast = native.use("name")
       return fast(...) if fast is not None else _twin(...)

3. Test in `tests/test_native.py`: equal to the twin on random inputs (1e-12 unless the routine says otherwise),
   empty input, NaN, one value, the threaded path.
4. Measure it against the twin and write the numbers in the step of the plan.
5. New crates: MIT, Apache-2.0 or BSD only; add them to THIRD_PARTY.md. `cargo update` only on purpose, then
   commit `Cargo.lock`.
