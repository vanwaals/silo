#!/usr/bin/env python

import itertools
import platform
import subprocess
import sys

#DBS = ('mysql', 'bdb', 'ndb-proto1', 'ndb-proto2')
#DBS = ('ndb-proto1', 'ndb-proto2')
#DBS = ('ndb-proto2', 'kvdb')
DBS = ('kvdb', 'ndb-proto2')

# config for tom
#THREADS = (1, 2, 4, 8, 12, 18, 24, 30, 36, 42, 48)
#THREADS = (1,)

# config for ben
#THREADS = (1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80)

# config for istc*
THREADS = (1, 4, 8, 12, 16, 20, 24, 28, 32)

#TXN_FLAGS = (0x0, 0x1)
#TXN_FLAGS = (0x1,)

#SCALE_FACTORS = (10,)

# tuples of (benchname, amplification-factor)
#BENCHMARKS = ( ('ycsb', 1000), ('tpcc', 1), )

NTRIALS = 3

### NOTE: for TPC-C, in general, allocate 4GB of memory per thread for the experiments.
### this is over-conservative

grids = []

# exp 1:
#   scale graph: kvdb VS ndb on ycsb 80/20 w/ fixed scale factor 320000

#grids += [
#  {
#    'name' : 'scale',
#    'dbs' : DBS,
#    'threads' : THREADS,
#    'scale_factors' : [320000],
#    'benchmarks' : ['ycsb'],
#    'bench_opts' : ['--workload-mix 80,20,0,0'],
#    'par_load' : [True],
#    'retry' : [False],
#  },
#  {
#    'name' : 'scale_rmw',
#    'dbs' : DBS,
#    'threads' : THREADS,
#    'scale_factors' : [320000],
#    'benchmarks' : ['ycsb'],
#    'bench_opts' : ['--workload-mix 80,0,20,0'],
#    'par_load' : [True],
#    'retry' : [False],
#  },
#]

def mk_ycsb_entries(nthds):
  return [
    {
      'name' : 'scale',
      'dbs' : DBS,
      'threads' : [nthds],
      'scale_factors' : [320000],
      'benchmarks' : ['ycsb'],
      'bench_opts' : ['--workload-mix 80,20,0,0'],
      'par_load' : [True],
      'retry' : [False],
      'numa_memory' : ['%dG' % int(100 + 1.4*nthds)],
    },
    {
      'name' : 'scale_rmw',
      'dbs' : DBS,
      'threads' : [nthds],
      'scale_factors' : [320000],
      'benchmarks' : ['ycsb'],
      'bench_opts' : ['--workload-mix 80,0,20,0'],
      'par_load' : [True],
      'retry' : [False],
      'numa_memory' : ['%dG' % int(100 + 1.4*nthds)],
    },
  ]
for nthds in THREADS:
  grids += mk_ycsb_entries(nthds)

# exp 2:
def mk_grid(name, bench, nthds):
  return {
    'name' : name,
    'dbs' : ['ndb-proto2'],
    'threads' : [nthds],
    'scale_factors' : [nthds],
    'benchmarks' : [bench],
    'bench_opts' : [''],
    'par_load' : [False],
    'retry' : [False],
    'numa_memory' : ['%dG' % (4 * 28)],
  }
grids += [mk_grid('scale_tpcc', 'tpcc', t) for t in THREADS]

# exp 3:
#   x-axis varies the % multi-partition for new order. hold scale_factor constant @ 28,
#   nthreads also constant at 28
D_RANGE = range(0, 11)
grids += [
  {
    'name' : 'multipart:pct',
    'dbs' : ['ndb-proto2'],
    'threads' : [28],
    'scale_factors': [28],
    'benchmarks' : ['tpcc'],
    'bench_opts' : ['--workload-mix 100,0,0,0,0 --new-order-remote-item-pct %d' % d for d in D_RANGE],
    'par_load' : [False],
    'retry' : [False],
    'numa_memory' : ['%dG' % (4 * 28)],
  },
  {
    'name' : 'multipart:pct',
    'dbs' : ['kvdb-st'],
    'threads' : [28],
    'scale_factors': [28],
    'benchmarks' : ['tpcc'],
    'bench_opts' :
      ['--workload-mix 100,0,0,0,0 --enable-separate-tree-per-partition --enable-partition-locks --new-order-remote-item-pct %d' % d for d in D_RANGE],
    'par_load' : [True],
    'retry' : [False],
    'numa_memory' : ['%dG' % (4 * 28)],
  },
]

# exp 4:
#  * standard workload mix
#  * fix the tpc-c scale factor at 8
#  * for volt, do one run @ 8-threads
#  * for ndb, vary threads [8, 12, 16, 20, 24, 28, 32]
#grids += [
#  {
#    'name' : 'multipart:cpu',
#    'dbs' : ['kvdb'],
#    'threads' : [8],
#    'scale_factors': [8],
#    'benchmarks' : ['tpcc'],
#    'bench_opts' : ['--enable-separate-tree-per-partition --enable-partition-locks'],
#    'par_load' : [True],
#    'retry' : [False],
#  },
#  {
#    'name' : 'multipart:cpu',
#    'dbs' : ['ndb-proto2'],
#    'threads' : [8, 12, 16, 20, 24, 28, 32],
#    'scale_factors': [8],
#    'benchmarks' : ['tpcc'],
#    'bench_opts' : [''],
#    'par_load' : [False],
#    'retry' : [False],
#  },
#]

# exp 5:
#  * 50% new order, 50% stock level
#  * scale factor 8, n-threads 16
#  * x-axis is --new-order-remote-item-pct from [0, 20, 40, 60, 80, 100]
RO_DRANGE = [0, 20, 40, 60, 80, 100]
grids += [
  {
    'name' : 'readonly',
    'dbs' : ['ndb-proto2'],
    'threads' : [16],
    'scale_factors': [8],
    'benchmarks' : ['tpcc'],
    'bench_opts' : ['--workload-mix 50,0,0,0,50 --new-order-remote-item-pct %d' % d for d in RO_DRANGE],
    'par_load' : [False],
    'retry' : [True],
    'numa_memory' : ['%dG' % (4 * 16)],
  },
  {
    'name' : 'readonly',
    'dbs' : ['ndb-proto2'],
    'threads' : [16],
    'scale_factors': [8],
    'benchmarks' : ['tpcc'],
    'bench_opts' : ['--disable-read-only-snapshots --workload-mix 50,0,0,0,50 --new-order-remote-item-pct %d' % d for d in RO_DRANGE],
    'par_load' : [False],
    'retry' : [True],
    'numa_memory' : ['%dG' % (4 * 16)],
  },
]

def run_configuration(basedir, dbtype, bench, scale_factor, nthreads, bench_opts, par_load, retry_aborted_txn, numa_memory):
  args = [
      './dbtest',
      '--bench', bench,
      '--basedir', basedir,
      '--db-type', dbtype,
      '--num-threads', str(nthreads),
      '--scale-factor', str(scale_factor),
      '--txn-flags', '1',
      '--runtime', '60',
  ] + ([] if not bench_opts else ['--bench-opts', bench_opts]) \
    + ([] if not par_load else ['--parallel-loading']) \
    + ([] if not retry_aborted_txn else ['--retry-aborted-transactions']) \
    + ([] if not numa_memory else ['--numa-memory', numa_memory])
  print >>sys.stderr, '[INFO] running command %s' % str(args)
  p = subprocess.Popen(args, stdin=open('/dev/null', 'r'), stdout=subprocess.PIPE)
  r = p.stdout.read()
  p.wait()
  toks = r.strip().split(' ')
  assert len(toks) == 2
  return float(toks[0]), float(toks[1])

if __name__ == '__main__':
  (_, basedir, outfile) = sys.argv

  # iterate over all configs
  results = []
  for grid in grids:
    for (db, bench, scale_factor, threads, bench_opts, par_load, retry, numa_memory) in itertools.product(
        grid['dbs'], grid['benchmarks'], grid['scale_factors'], \
        grid['threads'], grid['bench_opts'], grid['par_load'], grid['retry'],
        grid['numa_memory']):
      config = {
        'name'         : grid['name'],
        'db'           : db,
        'bench'        : bench,
        'scale_factor' : scale_factor,
        'threads'      : threads,
        'bench_opts'   : bench_opts,
        'par_load'     : par_load,
        'retry'        : retry,
        'numa_memory'  : numa_memory,
      }
      print >>sys.stderr, '[INFO] running config %s' % (str(config))
      values = []
      for _ in range(NTRIALS):
        value = run_configuration(basedir, db, bench, scale_factor, threads, bench_opts, par_load, retry, numa_memory)
        values.append(value)
      results.append((config, values))

    # write intermediate results
    with open(outfile + '.py', 'w') as fp:
      print >>fp, 'RESULTS = %s' % (repr(results))

  # write results
  with open(outfile + '.py', 'w') as fp:
    print >>fp, 'RESULTS = %s' % (repr(results))
