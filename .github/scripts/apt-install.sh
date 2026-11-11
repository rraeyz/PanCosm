#!/bin/bash
# Install system packages on a GitHub runner. The runners' own Ubuntu mirror (azure.archive.ubuntu.com) could not be
# resolved for hours on 2026-11-11: after the first failure the sources point at a public mirror instead.
set -u
arch=$(dpkg --print-architecture)
mirror=http://mirrors.edge.kernel.org/ubuntu/
[ "$arch" = arm64 ] && mirror=http://mirrors.edge.kernel.org/ubuntu-ports/
for i in 1 2 3; do
  sudo apt-get update && sudo apt-get install -y "$@" && exit 0
  if [ "$i" = 1 ]; then
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
      [ -f "$f" ] && sudo sed -i -E "s#mirror\+file:/etc/apt/apt-mirrors.txt|https?://(azure\.)?archive\.ubuntu\.com/ubuntu/?|https?://security\.ubuntu\.com/ubuntu/?|https?://ports\.ubuntu\.com/ubuntu-ports/?#${mirror}#g" "$f"
    done
  fi
  sleep 20
done
exit 1
