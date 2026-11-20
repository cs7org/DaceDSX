# Work on Documentation

[//]: # (This chapter has been generated with AI and refined by hand.)

The documentation built with [**mdBook**](https://rust-lang.github.io/mdBook/), which compiles the Markdown files from `docs/src` into a static website. [**ReadTheDocs**](https://about.readthedocs.com/) is wrapped around that process to compile and upload the pages to this domain.

## Installation

mdBook is written in Rust, so the Rust toolchain has to be installed first:

1. **Install Rust and Cargo** via [rustup](https://www.rust-lang.org/tools/install):
    ```bash
    # For Linux
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    # For Windows
    winget install Rustlang.Rustup
    ```
2. **Install the mdBook crate**:
    ```bash
    cargo install mdbook
    # verify successful installation
    mdbook --version
    ```

## Writing Documentation

- Add or edit pages in `docs/src` and register every new page in `docs/src/SUMMARY.md` (the table of contents of the book).
- mdBook uses its own [Markdown variation](https://rust-lang.github.io/mdBook/format/markdown.html), with extensions such as `[!NOTE]` admonitions and footnotes. Refer to the [mdBook documentation](https://rust-lang.github.io/mdBook/) for the full format description and the configuration options in `docs/book.toml`.

## Previewing Changes

For a live preview in the browser, use `mdbook serve` - it watches for changes as well and serves the book with automatic reload:

```bash
# in directory of repository
mdbook serve docs
# then open http://localhost:3000
```

## Building the Book

To build the static HTML once:

```bash
# in directory of repository
mdbook build docs
# output is written to docs/book
```
