#!/bin/bash
tmsh -c 'show ltm pool /*/* field-fmt raw' > pool_snapshot_$(date +%Y%m%d_%H%M%S).txt
