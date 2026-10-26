#!/bin/bash
export PATH=/opt/homebrew/bin:$PATH
echo "=== install cmake ===" >> ~/build_flint.log 2>&1
brew install cmake >> ~/build_flint.log 2>&1
echo "=== configure ===" >> ~/build_flint.log 2>&1
cd ~/llama.cpp
cmake -B build -DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=OFF >> ~/build_flint.log 2>&1
echo "=== build ===" >> ~/build_flint.log 2>&1
cmake --build build --config Release -j $(sysctl -n hw.ncpu) --clean-first --target llama-server llama-cli >> ~/build_flint.log 2>&1
echo "=== copy binaries ===" >> ~/build_flint.log 2>&1
mkdir -p ~/bin
cp build/bin/llama-server ~/bin/llama-server
cp build/bin/llama-cli ~/bin/llama-cli
echo "BUILD DONE" >> ~/build_flint.log
