"""Separate benchmark on the published Colombian upland rice breeding trial."""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import RepeatedKFold

from src.data import ROOT, digest
from src.model import scores


SOURCE = ROOT / 'data/raw/rice/colombia_aluminium'
REPORT = ROOT / 'docs/Aluminium_Study_Results.json'
RIDGE_PENALTY = 1.0  # Fixed penalty on a kernel scaled by the number of SNPs.


def run():
    """Compare fixed models on identical held-out families; never touch app artifacts."""
    receipt = json.loads((SOURCE / 'source.json').read_text(encoding='utf-8-sig'))
    for file in receipt['files']:
        if digest(SOURCE / file['filename']) != file['sha256']:
            raise ValueError(f"Source checksum failed: {file['filename']}")

    path = SOURCE / 'Omicas_GP_genotypes.txt'
    with path.open(encoding='utf-8-sig') as stream:
        markers = next(stream).split()
    if len(markers) != 9928 or len(set(markers)) != len(markers):
        raise ValueError('Unexpected SNP header')
    snps = pd.read_csv(path, sep='\t', skiprows=1, header=None,
                       names=['DNAID', *markers], dtype={'DNAID': str}).set_index('DNAID')
    phenotypes = pd.read_csv(SOURCE / 'Omicas_GP_BLUEs.csv', dtype={'DNAID': str})
    families = phenotypes.loc[phenotypes['Gen'].eq('Fam')]
    yields = families.pivot(index='DNAID', columns='SOIL', values='YLD').sort_index()
    if (not snps.index.is_unique or set(snps.index) != set(yields.index)
            or yields.shape != (334, 2) or set(yields) != {'ALU', 'LIM'}
            or not np.isfinite(yields).all().all() or not yields.gt(0).all().all()):
        raise ValueError('Expected 334 matched families with one finite yield in each soil condition')
    markers_by_family = snps.loc[yields.index].to_numpy(dtype=float)
    if not np.isin(markers_by_family, [0, 1, 2]).all():
        raise ValueError('Unexpected genotype dosage')
    target = yields['ALU'].to_numpy()
    control = yields[['LIM']].to_numpy()

    methods = ['Training mean', 'Limed yield only', 'SNP only', 'Limed yield + SNP']
    predictions = {name: np.full((10, len(yields)), np.nan) for name in methods}
    splitter = RepeatedKFold(n_splits=5, n_repeats=10, random_state=42)
    for fold, (train, test) in enumerate(splitter.split(yields)):
        repeat = fold // 5
        if np.intersect1d(train, test).size or np.isfinite(predictions[methods[0]][repeat, test]).any():
            raise ValueError('Overlapping assessment families')
        avg = target[train].mean()
        limed = LinearRegression().fit(control[train], target[train])
        limed_test = limed.predict(control[test])
        # Fit centering and the linear control-yield term using training families only.
        x_train = markers_by_family[train]
        centre = x_train.mean(axis=0)
        x_train = x_train - centre
        x_test = markers_by_family[test] - centre
        kernel = x_train @ x_train.T / len(markers)
        kernel.flat[::len(train) + 1] += RIDGE_PENALTY
        cross = x_test @ x_train.T / len(markers)
        residuals = np.column_stack([target[train] - avg,
                                     target[train] - limed.predict(control[train])])
        genomic = cross @ np.linalg.solve(kernel, residuals)
        for name, values in zip(methods, [avg, limed_test, avg + genomic[:, 0],
                                          limed_test + genomic[:, 1]], strict=True):
            predictions[name][repeat, test] = values

    results = {}
    for name, matrix in predictions.items():
        if not np.isfinite(matrix).all():
            raise ValueError('Missing assessment predictions')
        results[name] = [{**scores(target, estimate),
                          'Pearson r': None if name == 'Training mean' else float(np.corrcoef(target, estimate)[0, 1])}
                         for estimate in matrix]
    averages = {name: {key: None if values[0][key] is None else float(np.mean([r[key] for r in values]))
                       for key in values[0]} for name, values in results.items()}
    return {
        'dataset': receipt['doi'], 'version': receipt['version'], 'source_receipt_sha256': digest(SOURCE / 'source.json'),
        'families': len(yields), 'SNPs': len(markers), 'target': 'Published adjusted ALU grain yield (kg/ha)',
        'assessment': 'Repeated family-level 5-fold cross-validation, 10 repeats, seed 42, one pooled score per repeat',
        'ridge_penalty': RIDGE_PENALTY, 'mean_scores': averages, 'repeat_scores': results,
        'limitations': ['One breeding population and one location-season; no unseen-site, year or district test.',
                        'LIM methods require measured limed-soil yield for the candidate family.',
                        'Published plot adjustments and SNP imputation were not refit inside these folds.',
                        'This is a fixed benchmark adaptation, not a replication of the authors’ GBLUP or a causal loss estimate.'],
    }


def write_report():
    report = run()
    REPORT.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return report['mean_scores']
