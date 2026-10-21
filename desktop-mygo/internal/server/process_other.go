//go:build !windows

package server

import (
	"os"
	"os/exec"
)

func prepareCommand(*exec.Cmd) {}

func terminateProcess(p *os.Process) {
	_ = p.Signal(os.Interrupt)
}

func guardProcess(int) (func(), error) {
	return func() {}, nil
}
