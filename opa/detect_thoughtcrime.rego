package detect_thoughtcrime

# Note variable and rule names can't start with same name as the
# package name. Because below called restricted_files, can't call package
# `restricted` or `restrict` or `r`!
restricted_files := {
	"necronomicon",
	"lady chatterley's hoover",
	"mr blobby annual",
}

default allow := false

# Rego has `in` keyword but comparision that uses `in` is difficult!
allow if not restricted_files[input.filename]

# Would be nice to have a startswith or substring comparison.
# Also case-insensitivity. But would take a while to work out
# how to do this!
