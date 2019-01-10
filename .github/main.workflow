workflow "Run tests" {
  on = "push"
  resolves = [
    "docker://python:3.7",
    "docker://python:3.6",
  ]
}

action "docker://python:3.7" {
  uses = "docker://python:3.7"
  runs = "python"
  args = "setup.py test"
}

action "docker://python:3.6" {
  uses = "docker://python:3.6"
  runs = "python"
  args = "setup.py test"
}
