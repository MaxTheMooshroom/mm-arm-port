#!/usr/bin/env python3
import sys
import os
import shlex
import subprocess
import tempfile
import asm_processor

dir_path = os.path.dirname(os.path.realpath(__file__))
prelude = os.path.join(dir_path, "prelude.inc")

all_args = sys.argv[1:]
sep0 = [index for index, arg in enumerate(all_args) if not arg.startswith("-")][0]
sep1 = all_args.index("--")
sep2 = all_args.index("--", sep1 + 1)

asmproc_flags = all_args[:sep0]
compiler = all_args[sep0:sep1]

assembler = all_args[sep1 + 1 : sep2]
assembler_sh = " ".join(shlex.quote(x) for x in assembler)

compile_args = all_args[sep2 + 1 :]
in_file = compile_args[-1]
out_ind = compile_args.index("-o")
out_file = compile_args[out_ind + 1]
del compile_args[-1]
del compile_args[out_ind + 1]
del compile_args[out_ind]

in_dir = os.path.split(os.path.realpath(in_file))[0]
opt_flags = [
    x for x in compile_args if x in ["-g3", "-g", "-O0", "-O1", "-O2", "-framepointer"]
]
if "-mips2" not in compile_args:
    opt_flags.append("-mips1")

asmproc_flags += opt_flags + [in_file]

# Drop .mdebug and .gptab sections from resulting binaries. This makes
# resulting .o files much smaller and speeds up builds, but loses line
# number debug data.
# asmproc_flags += ["--drop-mdebug-gptab"]

# Convert encoding before compiling.
# asmproc_flags += ["--input-enc", "utf-8", "--output-enc", "euc-jp"]

preprocessed_file = tempfile.NamedTemporaryFile(
    prefix="preprocessed", suffix=".c", delete=False
)

try:
    compile_cmdline = (
        compiler + compile_args + ["-I", in_dir, "-o", out_file, preprocessed_file.name]
    )

    functions, deps = asm_processor.run(asmproc_flags, outfile=preprocessed_file)
    try:
        subprocess.check_call(compile_cmdline)
    except subprocess.CalledProcessError as e:
        print("Failed to compile file " + in_file + ". Command line:")
        print()
        print(" ".join(shlex.quote(x) for x in compile_cmdline))
        print()
        sys.exit(55)
        # To keep the preprocessed file:
        # os._exit(1)

    asm_processor.run(
        asmproc_flags
        + [
            "--post-process",
            out_file,
            "--assembler",
            assembler_sh,
            "--asm-prelude",
            prelude,
        ],
        functions=functions,
    )

    deps_file = out_file[:-2] + ".asmproc.d"
    if deps:
        with open(deps_file, "w") as f:
            f.write(out_file + ": " + " \\\n    ".join(deps) + "\n")
            for dep in deps:
                f.write("\n" + dep + ":\n")
    else:
        try:
            os.remove(deps_file)
        except OSError:
            pass
finally:
    os.remove(preprocessed_file.name)
