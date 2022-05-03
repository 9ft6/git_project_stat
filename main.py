import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


def run_process(command, callback=print):
    kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'bufsize': -1,
        'universal_newlines': True,
    }
    process = subprocess.Popen(command, **kwargs)

    in_progress = True
    results = []
    while in_progress:
        try:
            output = process.stdout.readline()
        except:
            output = 'bad encoding'

        if callback:
            if result := callback(output.strip()):
                results.append(result)

        in_progress = bool(output)
    return results


def get_commits():
    result = []
    body = '\n'.join(run_process(['git', 'log'], callback=lambda x: x))
    commits = [x.replace('commit ', '') for x in body.split('\ncommit ') if x]
    for commit in commits:
        hash, author, date, *message = commit.split('\n')
        result.append({
            'hash': hash,
            'date': date.replace('Date:', '').strip(),
            'ts': int(datetime.strptime(date[:-6], 'Date:   %a %b %d %H:%M:%S %Y').timestamp()),
            'author': author,
            'message': '\n'.join(message),
        })
    return result


def set_commit(commit):
    run_process(['git', 'checkout', commit['hash']], callback=lambda x: x)


def count_commit(commit):
    command = ['cloc', '--exclude-list-file=.gitignore', '.']
    logs = run_process(command, callback=lambda x: x)
    title = []
    for line in logs:
        if line.endswith(' text files.'):
            commit['text_files'] = int(line.split(' text files.')[0])
        elif line.endswith(' unique files.'):
            commit['unique_files'] = int(line.split(' unique files.')[0])
        elif line.endswith(' files ignored.'):
            commit['ignored_files'] = int(line.split(' files ignored.')[0])
        elif line.startswith('Language'):
            title = line.split()[1:]
        elif line.startswith('Python'):
            counts = line.split()[1:]
            commit['python'] = {k: int(v) for k, v in zip(title, counts)}
    return commit


def checkout_head():
    run_process(['git', 'switch', 'main'])


def collect_commits(project_path):
    os.chdir(project_path)
    commits = get_commits()
    for commit in commits:
        set_commit(commit)
        count_commit(commit)
    checkout_head()
    return commits


def plot(commits):
    tss = []
    code = []
    blanks = []
    files = []
    comments = []

    min_ts = None
    for commit in sorted(commits, key=lambda x: x['ts']):
        if not min_ts:
            min_ts = commit['ts']

        tss.append((commit['ts'] - min_ts) / 3600)
        blanks.append(commit['python']['blank'])
        files.append(commit['python']['files'])
        comments.append(commit['python']['comment'])
        code.append(commit['python']['code'])
        print(json.dumps(commit, indent=4))

    total = [sum(x) for x in zip(code, comments, blanks)]

    plt.figure(figsize=(13,13))
    plt.title(f'Python project statistic:\n{project_path} {len(total)} commits')
    plt.plot(tss, code, 'go', label='code lines')
    plt.plot(tss, blanks, 'bo', label='blank lines')
    plt.plot(tss, comments, 'ro', label='comment lines')
    plt.plot(tss, files, 'b*', label='files in project')
    plt.plot(tss, total, 'yo', label='total lines')
    plt.xlabel('hours')
    plt.ylabel('value')
    plt.legend(loc='best')
    plt.show()


def dump(commits, filename):
    report_path.parent.mkdir(exist_ok=True)
    with open(filename, 'w') as file:
        json.dump(commits, file, indent=4)
        print(f'commits report: "{filename}"')


def load(filename):
    report_path.parent.mkdir(exist_ok=True)
    with open(filename, 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    project_path = Path('/home/ft/py/temp').absolute()
    report_path = project_path / 'reports' / 'report.json'

    dump(collect_commits(project_path), report_path)
    plot(load(report_path))

