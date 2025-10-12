# From https://tex.stackexchange.com/questions/58963/latexmk-with-makeglossaries-and-auxdir-and-outdir#59098
add_cus_dep('glo', 'gls', 0, 'makeglossaries');
sub makeglossaries {
  my ($base_name, $path) = fileparse($_[0]);
  pushd $path if $path;
  my $return = system "makeglossaries $base_name";
  popd if $path;
  return $return;
}

$success_cmd = 'make _fachschaft-print';

# Do not override biber/bibtex here. We'll handle biber from the Makefile to
# ensure it runs in the project root so relative bib paths resolve correctly.
