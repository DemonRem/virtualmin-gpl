#!/usr/local/bin/perl
# Upgrade some script on multiple servers at once

require './virtual-server-lib.pl';
&ReadParse();
&error_setup($text{'massscript_err'});

# Parse inputs
($sname, $ver) = split(/\s+/, $in{'script'});
if ($in{'servers_def'}) {
	@doms = &list_domains();
	}
else {
	foreach my $s (split(/\0/, $in{'servers'})) {
		push(@doms, &get_domain($s));
		}
	@doms || &error($text{'massscript_enone'});
	}
foreach my $d (@doms) {
	&can_edit_domain($d) && &can_edit_scripts() ||
		&error($text{'edit_ecannot'});
	}

# Work out who has it
foreach my $d (@doms) {
	@got = &list_domain_scripts($d);
	@dsinfos = grep { $_->{'name'} eq $sname } @got;
	foreach $sinfo (@dsinfos) {
		$sinfo->{'dom'} = $d;
		}
	push(@sinfos, @dsinfos);
	}
@sinfos || &error($text{'massscript_enone2'});

&ui_print_unbuffered_header(undef, $text{'massscript_title'}, "");
$script = &get_script($sname);
print &text('massstart_start', $script->{'desc'},
			       $ver, scalar(@sinfos)),"<p>\n";

# Fetch needed files
$ferr = &fetch_script_files($sinfos[0]->{'dom'}, $ver, $sinfos[0]->{'opts'},
	    		    $sinfos[0], \%gotfiles);
&error($ferr) if ($ferr);

# Do each server that has it
foreach $sinfo (@sinfos) {
	$d = $sinfo->{'dom'};
	&$first_print(&text('massscript_doing', $d->{'dom'},
			    $sinfo->{'version'}, $sinfo->{'desc'}));
	if (&compare_versions($sinfo->{'version'}, $ver) >= 0) {
		# Already got it
		&$second_print(&text('massscript_ever', $sinfo->{'version'}));
		}
	elsif ($derr = &{$script->{'depends_func'}}($d, $ver)) {
		# Failed depends
		&$second_print(&text('massscript_edep', $derr));
		}
	else {
		# Setup PHP version
		$phpvfunc = $script->{'php_vers_func'};
		if (defined(&$phpvfunc)) {
			@vers = &$phpvfunc($d, $ver);
			if (!&setup_php_version($d, \@vers, $opts->{'path'})) {
				&error(&text('scripts_ephpvers',
					     join(" ", @vers)));
				}
			}

		# Go ahead and do it
		($ok, $msg, $desc, $url) = &{$script->{'install_func'}}($d, $ver, $sinfo->{'opts'}, \%gotfiles, $sinfo);
		&$indent_print();
		print $msg,"<br>\n";
		&$outdent_print();
		if ($ok) {
			# Worked .. record it
			&$second_print($text{'setup_done'});
			&remove_domain_script($d, $sinfo);
			&add_domain_script($d, $sname, $ver, $sinfo->{'opts'},
					   $desc, $url);
			}
		else {
			&$second_print($text{'scripts_failed'});
			last if ($in{'fail'});
			}
		}
	}

&webmin_log("upgrade", "scripts", scalar(@sinfos));
&ui_print_footer("", $text{'index_return'});


