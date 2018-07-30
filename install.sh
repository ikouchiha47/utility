#!/usr/bin/bash

path=$(echo $PATH)
targetdir="${HOME}/.local/bin"
echo "Checking if $targetdir exists"
files="kongsly,whatsmyip"

if [[ -d "$targetdir" ]]; then
  echo "$targetdir found"
else
  echo "Creating $targetdir"
  mkdir -p "$targetdir"
fi

echo "Checking if $targetdir is in PATH"
exists=$(echo $path | grep "${HOME}/.local/bin")

add_to_bashrc=0
add_to_zshrc=0
add_to_fishrc=0

if [[ -f "${HOME}/.bashrc" ]]; then
  if [[ -z $(cat "${HOME}/.bashrc" | grep "$targetdir") ]]; then
    add_to_bashrc=1
  fi
fi

if [[ -f "${HOME}/.zshrc" ]]; then
  if [[ -z $(cat "${HOME}/.zshrc" | grep "$targetdir") ]]; then
    add_to_zshrc=1
  fi
fi

if [[ -f "${HOME}/.config/fish/config.fish" ]]; then
  if [[ -z $(cat "${HOME}/.config/fish/config.fish" | grep "$targetdir") ]]; then
    add_to_fishrc=1
  fi
fi

if [[ -z $exists ]] ; then
  echo "${HOME}/.local/bin doesnot exists in PATH. adding to PATH"
  export PATH="$PATH:$targetdir"
fi


if [[ -f "${HOME}/.bashrc" ]] && [[ "$add_to_bashrc" -eq 1 ]]; then
  echo "export PATH=\"\$PATH:$targetdir\"" | tee -a "${HOME}/.bashrc"
fi

if [[ -f "${HOME}/.zshrc" ]] && [[ "$add_to_zshrc" -eq 1 ]]; then
  echo "export PATH=\"\$PATH:$targetdir\"" | tee -a "${HOME}/.zshrc"
fi

if [[ -f "${HOME}/.config/fish/config.fish" ]] && [[ "$add_to_fishrc" -eq 1 ]]; then
  echo "set -gx PATH \$PATH $targetdir" | tee -a "${HOME}/.config/fish/config.fish"
fi

echo "Moving files to $targetdir"
echo "$files" | tr "," "\n" | xargs -I {} cp {}.py $targetdir/{}

echo "Making files executable whith chmod +x file_name"
echo "$files" | tr "," "\n" | xargs -I {} chmod +x $targetdir/{}

echo "please source your .bashrc or .zshrc or config.fish file depending on your shell"
