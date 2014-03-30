#!/usr/bin/perl -T
$MIRROR_ROOT = "/home/sudomirror/public_html/mirror/";
chdir($MIRROR_ROOT) or die "chdir(): $!\n";
$ENV{PATH} = '/home/sudomirror/bin:/usr/local/bin:/usr/bin:/bin';
# cd ~/public_html/mirror/svn/ (Create it if needed)
$FAST = 1;

sub get_symlink_path($$$)
{
    my ($proto, $domain, $url_path) = @_;
    my $symlink_path = $MIRROR_ROOT."svn-$proto-roots/$domain";
    my @path = split('/',$url_path);
    for my $arg (@path) {
        $symlink_path .= '/'.$arg;
    }
    return $symlink_path;
}

sub do_clone($)
{
        my $proto;
        my $domain;
        my $url_path;
        if ($_[0]=~/^(svn|http):\/\/([a-zA-Z.]+)\/([\/0-9_a-z]+)$/s) {
                $proto = $1;
                $domain = $2;
                $url_path = $3;
        } else {
                die "[svn-clonerepo.pl] Cannot parse repository URL: $_[0]\n";
        }
        my $symlink_path = &get_symlink_path($proto,$domain,$url_path);
        if (-l $symlink_path) {
            print "[svn-clonerepo.pl:] $symlink_path already exists, skipping mirror.\n";
            return;
        }

        my $INFO = `svn info $proto://$domain/$url_path`;
        my $INFO_root = undef;
        my $INFO_url = undef;
        if ($INFO=~/^Repository Root: (.*?)$/m) {
            $INFO_root = $1;
        }
        if ($INFO=~/^URL: (.*?)$/m) {
            $INFO_url = $1;
        }
        die "No URL found in svn info\n" unless defined $INFO_url;
        die "No root found in svn info\n" unless defined $INFO_root;
        my $repo_path;
        if (substr($_[0],0,length($INFO_root)) eq $INFO_root) {
            $repo_path = $INFO_root;
        } else {
            die "Error: Cloning a repo that's not inside its own root?\n";
        }
        $repo_path=~s/^([a-z]+):\/\/([^\/]+)\///s;

        my @path = split('/',$repo_path);
        my $dir = $path[0];
        my $localdir = $MIRROR_ROOT.'svn';
        $localdir .= '-'.$proto if ($proto ne 'svn');

        mkdir("$localdir",0777);
        $localdir .= "/$domain";
        mkdir("$localdir",0777);
        for my $arg (@path) {
                $localdir .= '/'.$arg;
                mkdir("$localdir",0777);
        }
        print "[svn-clonerepo:] Debug: localdir $localdir\n";
        die "Could not create $localdir: $!\n" unless -d "$localdir";
        system('svnadmin', 'create', "$localdir");

        if ($FAST and $proto eq 'svn') {
                my $rev;
                if ($INFO=~/^Revision: ([0-9]+)$/m) {
                        $rev = $1;
                } else {
                        die "Error: Could not find revision in [$INFO].\n";
                }
                system("svnrdump dump -r$rev $proto://$domain/$repo_path >$MIRROR_ROOT/tmp/$$.svn.dump");
                if ($?) {
                        die "[svn-clonerepo.pl]: 'svnrdump dump -r$rev $proto://$domain/$repo_path >$MIRROR_ROOT/tmp/$$.svn.dump' failed with $?\n";
                }
                system("svnadmin load $localdir < $MIRROR_ROOT/tmp/$$.svn.dump");
                die "svnadmin load failed with $?\n" if $?;
                unlink("$MIRROR_ROOT/tmp/$$.svn.dump") or die "Could not delete tempfile.\n";
        } else {
                local *F;
                my $fn = "$localdir/hooks/pre-revprop-change";
                open(F,">$fn") or die "Cannot open $fn: $!\n";
                die "$!\n" unless print F "#!/bin/sh\n";
                die "$!\n" unless close(F);
                chmod(0755,$fn) or die "Error $! chmodding $fn\n";
                print "About to run 'svnsync init file://$localdir $proto://$domain/$repo_path\'\n";
                system("svnsync","init", "file://$localdir", "$proto://$domain/$repo_path");
                print "[svn-clonerepo:] Debug: svnsync init returned $?\n";
                system("svnsync", "sync", "file://$localdir");
                print "[svn-clonerepo:] Debug: svnsync sync returned $?\n";
        }
        if ($INFO_root ne $_[0]) {
            my @path = split('/',$symlink_path);
            pop(@path);
            my $dir = '';
            for my $arg (@path) {
                $dir .= "/$arg";
                mkdir($dir,0777);
            }
            if (!-d $dir) {
                die "[svn-clonerepo] $dir is not a dir.\n";
            }
            print "Debug: would like to symlink $localdir to $symlink_path";
            symlink($localdir,$symlink_path) or die "[svn-clonerepo:] symlink error: $!\n";
        }
}


for my $arg (@ARGV) {
        if ($arg eq '--slow') {
                $FAST = 0;
        } else {
                &do_clone($arg);
        }
}
