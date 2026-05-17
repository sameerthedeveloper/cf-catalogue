<?php
# BEGIN WP Cache by 10Web
define( 'WP_CACHE', true );
define( 'TWO_PLUGIN_DIR_CACHE', '/home/u442694130/domains/digitalpanda.website/public_html/cinemafocus/wp-content/plugins/tenweb-speed-optimizer/' );
# END WP Cache by 10Web
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the web site, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * Localized language
 * * ABSPATH
 *
 * @link https://wordpress.org/support/article/editing-wp-config-php/
 *
 * @package WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', "i7421339_wp2" );

/** Database username */
define( 'DB_USER', "i7421339_wp2" );

/** Database password */
define( 'DB_PASSWORD', "N.85zdmQPDnsBUnmFzG35" );

/** Database hostname */
define( 'DB_HOST', "localhost" );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );


/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY',          '=lD]rdr%}ypjn`Y1RNLW$@~xS@d%Cj`;xjZ&a|]T}l$+x4QhDb1yJ(Wh.Dcz}oZS' );
define( 'SECURE_AUTH_KEY',   'Fm|k==l[@<[gzv+RaYvkv*NOH#`eMd/};p9N<AR)Pj;|SH%<<aX8N`u(/:DBX)~@' );
define( 'LOGGED_IN_KEY',     '@doU(4ge}2r[)CYBPE2>m_SOdf6%`$O7U1ur~.WU:OYn6^jkOXj!_(%2lQUSo.j+' );
define( 'NONCE_KEY',         'y4*LEC+iX9(BU_[{ONPUh?S9)N.vyM0+=vZB|J!SnJ&ef:.JlfHAL:bs*[w>;dyU' );
define( 'AUTH_SALT',         '6ukGo}wU%a48C=!r;?;;CG}[Dg/ Q1dMBCDsv$>&z{@#?H`:WxUZ_Jy0<0#QcUVP' );
define( 'SECURE_AUTH_SALT',  'XPtM{y8se6:1k}i=qn1gT@>eu=V@YTw&FY]znO#[V(LvXz#2+$+~0~njeF&yJ/31' );
define( 'LOGGED_IN_SALT',    '|aqcA-kOXD,v7Ob~#C^lc&fl1%8,#Yub;V])plU>x~TF+pBJ?[1GIWja3L&?zk3$' );
define( 'NONCE_SALT',        '}F<%?7gwQKTP7dYuk0}}F/_}T`)ikLs&.]iC~E_2tdXhvUgT=JaU1LQ:Mq|t2Ek$' );
define( 'WP_CACHE_KEY_SALT', 'il}XvNWl(=pk,&$6yV :^^+?b_p2?]n[mX@_Gka$wmNY>NjBj%zf; 3T8~%J:kE$' );


/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://wordpress.org/support/article/debugging-in-wordpress/
 */
define( 'WP_DEBUG', false );


/* Add any custom values between this line and the "stop editing" line. */



define( 'FS_METHOD', 'direct' );
define( 'WP_AUTO_UPDATE_CORE', 'minor' );
define( 'DUPLICATOR_AUTH_KEY', 'iZ/F1?X}(hiL>=VH[0s+2F8LEfA Lt*NPi: &9:AQ>yk(0Z1{b7W~J-<(DLx]85c' );
/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
