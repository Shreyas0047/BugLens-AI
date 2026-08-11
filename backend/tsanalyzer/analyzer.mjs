/**
 * Bug Lens-Ai TS/JS static analyzer (ts-morph).
 *
 * Usage: node analyzer.mjs <workspace> [ignore_dir,ignore_dir,...]
 * Output (JSON on stdout):
 * {
 *   "findings":  [ {source,type,category,file,line,column,message,description,confidence,evidence} ],
 *   "imports":   [ [fromFile, toFile] ],
 *   "complexity": { file: { fnName: cc } },
 *   "toolResult": { available: bool, error: str|null }
 * }
 */

import { Project, SyntaxKind } from 'ts-morph'
import { existsSync, readFileSync } from 'node:fs'
import { join, relative, resolve, extname } from 'node:path'

const [, , workspaceArg, ignoreArg] = process.argv
const workspace = resolve(workspaceArg || '.')
const ignoreDirs = (ignoreArg || 'node_modules,dist,build,target,.git,.venv,venv,coverage,.next')
  .split(',')
  .filter(Boolean)

const out = { findings: [], imports: [], complexity: {}, toolResult: { available: false, error: null } }

if (!existsSync(workspace)) {
  out.toolResult.error = 'workspace does not exist'
  console.log(JSON.stringify(out))
  process.exit(0)
}

function walk(dir, acc = []) {
  let entries
  try {
    entries = readdirSafe(dir)
  } catch {
    return acc
  }
  for (const entry of entries) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (ignoreDirs.includes(entry.name)) continue
      walk(full, acc)
    } else if (entry.isFile() && ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'].includes(extname(entry.name))) {
      acc.push(full)
    }
  }
  return acc
}

import { readdirSync } from 'node:fs'
function readdirSafe(dir) {
  return readdirSync(dir, { withFileTypes: true })
}

const files = walk(workspace)
if (files.length === 0) {
  out.toolResult.error = 'no TS/JS files found'
  console.log(JSON.stringify(out))
  process.exit(0)
}

const project = new Project({
  useInMemoryFileSystem: false,
  skipAddingFilesFromTsConfig: true,
  compilerOptions: {
    allowJs: true,
    checkJs: false,
    noEmit: true,
    skipLibCheck: true,
    skipDefaultLibCheck: true,
    allowNonTsExtensions: true,
    noResolve: true,
  },
})

for (const file of files) {
  try {
    project.addSourceFileAtPath(file)
  } catch {
    /* skip unparseable */
  }
}

const sources = project.getSourceFiles()
const relPath = (f) => relative(workspace, f).split('\\').join('/')

// --- import graph (module-level edges, file -> file) ---
for (const sf of sources) {
  const from = relPath(sf.getFilePath())
  for (const mod of sf.getImportDeclarations()) {
    const target = mod.getModuleSpecifierValue()
    const resolved = resolveModule(sf.getFilePath(), target)
    if (resolved && sources.some((s) => s.getFilePath() === resolved)) {
      out.imports.push([from, relPath(resolved)])
    }
  }
}

function resolveModule(fromFile, specifier) {
  if (!specifier.startsWith('.')) return null
  const base = resolve(fromFile, '..', specifier)
  const candidates = [base, `${base}.ts`, `${base}.tsx`, `${base}.js`, `${base}.jsx`, `${base}.mjs`, `${base}/index.ts`, `${base}/index.tsx`, `${base}/index.js`]
  for (const c of candidates) {
    if (existsSync(c)) return c
  }
  return null
}

// --- unused symbols + complexity ---
function approxComplexity(fnDecl) {
  let cc = 1
  const visit = (node) => {
    const kind = node.getKind()
    if ([
      SyntaxKind.IfStatement, SyntaxKind.ForStatement, SyntaxKind.ForInStatement,
      SyntaxKind.ForOfStatement, SyntaxKind.WhileStatement, SyntaxKind.DoStatement,
      SyntaxKind.CaseClause, SyntaxKind.CatchClause, SyntaxKind.ConditionalExpression,
    ].includes(kind)) cc += 1
    if ([SyntaxKind.AmpersandAmpersandToken, SyntaxKind.BarBarToken].includes(kind)) cc += 1
    node.getChildren().forEach(visit)
  }
  visit(fnDecl)
  return cc
}

function addFinding(type, category, file, decl, message, confidence, detail) {
  const line = decl.getStartLineNumber()
  out.findings.push({
    source: 'ts-morph',
    type,
    category,
    file: relPath(file),
    line,
    column: decl.getStart().getColumn() - 1,
    message,
    description: detail || '',
    confidence,
    evidence: { rule: type, snippet: decl.getText().slice(0, 800) },
  })
}

const MAX_UNUSED_FINDINGS = 300
let unusedCount = 0

for (const sf of sources) {
  const filePath = sf.getFilePath()
  const fileRel = relPath(filePath)

  // complexity of functions/methods
  const fnBlock = { name: 'unknown', cc: 0 }
  for (const fn of [...sf.getFunctions(), ...sf.getClasses().flatMap((c) => c.getMethods())]) {
    const name = fn.getName() || '<anonymous>'
    const cc = approxComplexity(fn)
    if (!out.complexity[fileRel]) out.complexity[fileRel] = {}
    out.complexity[fileRel][name] = cc
    if (cc > 15) {
      addFinding(
        'HIGH_COMPLEXITY', 'CODE_SMELL', filePath, fn,
        `Function '${name}' has approximate cyclomatic complexity ${cc} (threshold 15).`,
        0.7,
        `estimated cc=${cc}`,
      )
    }
  }

  // unused symbols: exported or module-private top-level declarations
  for (const decl of sf.getDescendantsOfKind(SyntaxKind.VariableDeclaration)) {
    const init = decl.getInitializer()
    if (init && (init.isKind(SyntaxKind.FunctionExpression) || init.isKind(SyntaxKind.ArrowFunction))) {
      const name = decl.getName()
      if (!name || name.startsWith('_')) continue
      const refs = decl.getSymbol()?.getReferencedSymbols() ?? []
      const external = refs.filter((r) => r.getDefinition().getSourceFile().getFilePath() !== filePath)
      if (refs.length === 0) {
        if (unusedCount < MAX_UNUSED_FINDINGS) {
          unusedCount++
          addFinding(
            'UNUSED_FUNCTION', 'CODE_SMELL', filePath, decl,
            `Function '${name}' is never referenced anywhere in the repository. May be dead code or an entry point (check framework registration).`,
            0.5,
            'dynamic use (frameworks, decorators, routes) cannot be proven statically',
          )
        }
      } else if (external.length > 0) {
        out.imports.push([fileRel, relPath(external[0].getDefinition().getSourceFile().getFilePath())])
      }
    }
  }

  for (const fn of sf.getFunctions()) {
    const name = fn.getName()
    if (!name || name.startsWith('_') || fn.isDefaultExport()) continue
    const refs = fn.getSymbol()?.getReferencedSymbols() ?? []
    if (refs.length === 0 && unusedCount < MAX_UNUSED_FINDINGS) {
      unusedCount++
      addFinding(
        'UNUSED_FUNCTION', 'CODE_SMELL', filePath, fn,
        `Function '${name}' is never referenced. May be dead code or an entry point (check framework registration).`,
        0.5,
        'dynamic use (frameworks, decorators, routes) cannot be proven statically',
      )
    }
  }

  for (const cls of sf.getClasses()) {
    const name = cls.getName()
    if (!name || name.startsWith('_')) continue
    const refs = cls.getSymbol()?.getReferencedSymbols() ?? []
    if (refs.length === 0 && unusedCount < MAX_UNUSED_FINDINGS) {
      unusedCount++
      addFinding(
        'UNUSED_CLASS', 'CODE_SMELL', filePath, cls,
        `Class '${name}' is never referenced. May be dead code or framework-registered.`,
        0.5,
        'dynamic use (frameworks, decorators, routes) cannot be proven statically',
      )
    }
  }
}

out.toolResult.available = true
console.log(JSON.stringify(out))
