# Installing SCIP-opt-suite 8.0.0

## Overview
This project requires SCIP-opt-suite version 8.0.0 to be compiled from the source code to include the Steiner Tree Solver. Please follow the instructions carefully to ensure that the correct components are installed.

## Important Notes
1. **Steiner Tree Solver must be compiled from the source code**: Do **not** download and install precompiled packages (such as `.deb` or `.exe` files).
2. **Use version 8.0.0**: Other versions may not include the source code for the Steiner Tree Solver.

## Download and Build Instructions

1. **Download SCIP-opt-suite 8.0.0 Source Code**: Obtain the source code from the [SCIP website](https://scipopt.org/).

2. **Extract the downloaded source code**.

3. **Compile using CMake**:
   - Create a build directory and navigate into it:
     ```bash
     mkdir build
     cd build
     ```

   - Run CMake with the `NO_EXTERNAL_CODE` option set to `ON`:
     ```bash
     cmake -DNO_EXTERNAL_CODE=ON ..
     ```

   - Compile the code:
     ```bash
     make
     ```

   - If you wish to compile in Debug mode, use the following command:
     ```bash
     cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
     ```

4. **Check for successful compilation**:
   - After a successful compilation, the `scip` executable should be generated in the `build/bin` directory. For more details on the compilation process, refer to the `INSTALL.md` file inside the `scip` directory.

5. **Compile the Steiner Tree Solver**:
   - Now that SCIP-opt-suite has been compiled, you need to compile the Steiner Tree Solver:
     ```bash
     cmake --build build --target scipstp
     ```

   - After successful compilation, the `scipstp` executable will be generated in the `build/bin/applications/` directory. For additional details on compiling the Steiner Tree Solver, refer to `INSTALL_APPLICATIONS_EXAMPLES.md` inside the `scip` directory.

## Additional Resources
For more comprehensive installation and compilation guidelines, please refer to the official documentation files (`INSTALL.md` and `INSTALL_APPLICATIONS_EXAMPLES.md`) within the downloaded source code.
